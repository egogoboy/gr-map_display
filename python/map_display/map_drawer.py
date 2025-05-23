import os
from matplotlib.font_manager import json
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib
from gnuradio import gr
import numpy as np
import pmt
import threading
import queue

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

        # Queue for coordinates
        self.q = queue.Queue()

        # Saved points
        self.data = []

        # GUI-stream start
        self.gui_thread = threading.Thread(target=self.run_gui, daemon=True)
        self.gui_thread.start()

        self.running = True


    def handle_msg(self, msg):
        if pmt.is_dict(msg):
            lon = pmt.to_double(pmt.dict_ref(msg, pmt.intern("lon"), pmt.from_double(0.0)))
            lat = pmt.to_double(pmt.dict_ref(msg, pmt.intern("lat"), pmt.from_double(0.0)))
            pitch = pmt.to_double(pmt.dict_ref(msg, pmt.intern("pitch"), pmt.from_double(0.0)))
            roll = pmt.to_double(pmt.dict_ref(msg, pmt.intern("roll"), pmt.from_double(0.0)))

            self.q.put({
                "lon": lon, 
                "lat": lat, 
                "pitch": pitch, 
                "roll": roll
            })



    def run_gui(self):
        print(LABEL, "GUI thread started")

        x0, x1 = 39.55, 39.65
        y0, y1 = 58.09, 58.18

        plt.ion()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.grid(True)
        ax.set_title("Map Display")

        try:
           module_dir = os.path.dirname(__file__)
           image_path = os.path.join(module_dir, 'assets', 'mok_map.png')

           print(LABEL, "Loading image from", image_path)
           if not os.path.exists(image_path):
               print("[Map Drawer]: Image not found at", image_path)
           else:
               map_img_obj = mpimg.imread(image_path)

               ax.imshow(map_img_obj,
                         extent=(x0, x1, y0, y1),
                         zorder=0)
               print(LABEL, "Background map displayed")

        except Exception as e:
           print(LABEL, "Can't load default background map:", str(e))

        # Point and path
        point, = ax.plot([], [], 'ro')
        path_line, = ax.plot([], [], 'b-')

        # Saved coordinates
        coords = []

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


        fig.canvas.mpl_connect('close_event', on_close)

        try:
            pitch_text = ax.text(1.02, 0.9, '', transform=ax.transAxes, fontsize=10, verticalalignment='top')
            roll_text = ax.text(1.02, 0.85, '', transform=ax.transAxes, fontsize=10, verticalalignment='top')
            while self.running:
                try:


                    item = self.q.get(timeout=0.1)
                    lat, lon = item["lat"], item["lon"]
                    pitch, roll = item["pitch"], item["roll"]

                    coords.append((lon, lat))
                    self.data.append(item)

                    xs, ys = zip(*coords)
                    path_line.set_data(xs, ys)
                    point.set_data([lon], [lat])

                    pitch_text.set_text(f"Pitch: {pitch:.1f}")
                    roll_text.set_text(f"Roll: {roll:.1f}")

                    fig.canvas.draw()
                    fig.canvas.flush_events()
                except queue.Empty:
                    continue

        except KeyboardInterrupt:
            print(LABEL, "Interrupted. Saving...")
        finally:
            plt.close(fig)
            plt.ioff()

        print(LABEL, "Gui thread stopped")
