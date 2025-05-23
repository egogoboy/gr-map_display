import time
import threading
import pmt
from gnuradio import gr
from gnuradio import blocks
from map_display import map_drawer

class test_top_block(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)
        self.drawer = map_drawer.map_drawer()

        # Нужен хотя бы один блок, чтобы flowgraph был валиден
        self.null_src = blocks.null_source(gr.sizeof_char)
        self.connect(self.null_src)

        # Запускаем генерацию сообщений
        self.gen_thread = threading.Thread(target=self.message_generator, daemon=True)
        self.gen_thread.start()

    def message_generator(self):
        lat = 55.75
        lon = 37.62
        pitch = 0
        roll = 0
        while True:
            lat += 0.001
            lon += 0.001
            pitch = (pitch + 1) % 360
            roll = (roll + 0.5) % 360

            msg_dict = pmt.make_dict()
            msg_dict = pmt.dict_add(msg_dict, pmt.intern("lat"), pmt.from_double(lat))
            msg_dict = pmt.dict_add(msg_dict, pmt.intern("lon"), pmt.from_double(lon))
            msg_dict = pmt.dict_add(msg_dict, pmt.intern("pitch"), pmt.from_double(pitch))
            msg_dict = pmt.dict_add(msg_dict, pmt.intern("roll"), pmt.from_double(roll))

            self.drawer.handle_msg(msg_dict)
            time.sleep(0.5)

if __name__ == '__main__':
    tb = test_top_block()
    tb.run()

