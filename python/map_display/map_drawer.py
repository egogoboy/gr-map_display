import os
import time
from matplotlib import pyplot as plt                                                                 
from matplotlib import image as mpimg                
import matplotlib
from aircraft_indicators import AttitudeIndicator, HeadingIndicator, DriftAngleIndicator, SpeedIndicator
from gnuradio import gr                                                                 
import numpy as np                                                                              
import pmt                                                                                      
import threading                                                                                 
import queue                                                                                   
import json

matplotlib.use('TkAgg')                         
LABEL = '[Map Drawer]: '

class map_drawer(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(
            self,
            name="map_drawer",
            in_sig=[],
            out_sig=[]
        )

        self.message_port_register_in(pmt.intern("in"))                                                                                                                                         
        self.set_msg_handler(pmt.intern("in"), self.handle_msg)

        self.q = queue.Queue()
        self.data = []
        self.gui_thread = threading.Thread(target=self.run_gui, daemon=True)
        self.gui_thread.start()
        self.running = True

                                                                                                 
    def handle_msg(self, msg):
        if pmt.is_dict(msg):
            lon = pmt.to_double(pmt.dict_ref(msg, pmt.intern("lon"), pmt.from_double(0.0)))
            lat = pmt.to_double(pmt.dict_ref(msg, pmt.intern("lat"), pmt.from_double(0.0))) 
            pitch = pmt.to_double(pmt.dict_ref(msg, pmt.intern("pitch"), pmt.from_double(0.0)))
            roll = pmt.to_double(pmt.dict_ref(msg, pmt.intern("roll"), pmt.from_double(0.0)))
            heading = pmt.to_double(pmt.dict_ref(msg, pmt.intern("heading"), pmt.from_double(0.0)))
            drift = pmt.to_double(pmt.dict_ref(msg, pmt.intern("drift"), pmt.from_double(0.0)))
            self.q.put({ 
                "lon": lon,
                "lat": lat,
                "pitch": pitch,
                "roll": roll,
                "heading": heading,
                "drift": drift
            })

    def run_gui(self):
        print(LABEL, "GUI thread started")

        x0, x1 = 39.55, 39.65
        y0, y1 = 58.09, 58.18

        plt.ion()
        fig, ax = plt.subplots(figsize=(13, 6))
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.grid(True)
        ax.set_title("Map Display")

        try:
            module_dir = os.path.dirname(__file__)
            image_path = os.path.join(module_dir, 'assets', 'mok_map.png')

            print(LABEL, "Loading image from", image_path)
            if os.path.exists(image_path):
                map_img_obj = mpimg.imread(image_path)
                ax.imshow(map_img_obj, extent=(x0, x1, y0, y1), zorder=0)
                print(LABEL, "Background map displayed")
            else:
                print(LABEL, "Image not found at", image_path)

        except Exception as e:
            print(LABEL, "Can't load default background map:", str(e))

        point, = ax.plot([], [], 'ro')
        path_line, = ax.plot([], [], 'b-')
        coords = []

        # attitude_ax = fig.add_axes([0.75, 0.7, 0.2, 0.2])
        attitude_widget = AttitudeIndicator(fig, position=[0.7, 0.2, 0.35, 0.35])
        heading_widget = HeadingIndicator(fig, position=[0.7, 0.6, 0.35, 0.35])
        drift_widget = DriftAngleIndicator(fig, position=[0.01, 0.2, 0.35, 0.35])
        speed_widget = SpeedIndicator(fig, position=[0.01, 0.6, 0.35, 0.35])

        def on_hover(event):
            if event.inaxes == ax:
                for entry in self.data:
                    dist = np.hypot(entry["lon"] - event.xdata, entry["lat"] - event.ydata)
                    if dist < 0.05:
                        print(LABEL, f"Hovered over: {entry}")
                        break
        fig.canvas.mpl_connect("motion_notify_event", on_hover)

        def on_close(event):
            print("Window closed, preparing to save data...")

            outdir = "/tmp/map_display_output"
            os.makedirs(outdir, exist_ok=True)

            img_path = os.path.join(outdir, "map.png")
            data_path = os.path.join(outdir, "route.json")
            fig.savefig(img_path)
            print(LABEL, f'Saved map image to {img_path}')

            with open(data_path, "w") as f:
                json.dump(self.data, f, indent=2)
            print(LABEL, f"Saved data to {data_path}")

            self.running = False

        def haversine(lat1, lon1, lat2, lon2):
            # Радиус Земли в км
            R = 6371.0
            # Переводим градусы в радианы
            phi1 = np.radians(lat1)
            phi2 = np.radians(lat2)
            d_phi = np.radians(lat2 - lat1)
            d_lambda = np.radians(lon2 - lon1)

            a = np.sin(d_phi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(d_lambda / 2.0)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

            return R * c  # в километрах

        fig.canvas.mpl_connect('close_event', on_close)

        try:
            past_lat = 0
            past_lon = 0
            past_time = time.time()

            while self.running:
                try:
                    item = self.q.get(timeout=0.1)
                    lat, lon = item["lat"], item["lon"]
                    pitch, roll = item["pitch"], item["roll"]
                    heading, drift = item["heading"], item["drift"]

                    coords.append((lon, lat))
                    self.data.append(item)

                    xs, ys = zip(*coords)
                    path_line.set_data(xs, ys)
                    point.set_data([lon], [lat])
                    cur_time = time.time()

                    if past_lat is not None and past_lon is not None:
                        distance_km = haversine(past_lat, past_lon, lat, lon)
                        delta_t = cur_time - past_time
                        speed_kmh = (distance_km / delta_t) * 3600  # км/ч

                        speed_kmh /= 10 # ONLY FOR PRESENTATION

                        speed_widget.update(speed_kmh)

                    attitude_widget.update(pitch, roll)
                    heading_widget.update(heading)
                    drift_widget.update(drift)

                    fig.canvas.draw()
                    fig.canvas.flush_events()

                    past_lat = lat
                    past_lon = lon
                    past_time = cur_time

                except queue.Empty:
                    continue

        except KeyboardInterrupt:
            print(LABEL, "Interrupted. Saving...")
        finally:
            plt.close(fig)
            plt.ioff()

        print(LABEL, "Gui thread stopped")

