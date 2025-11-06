#include <gnuradio/io_signature.h>
#include <gnuradio/logger.h>
#include <pmt/pmt.h>

#include "map_display/display_block.h"

namespace gr {
namespace map_display {

class display_block_impl : public display_block {
   private:
    gr::logger* d_logger;

   public:
    display_block_impl()
        : gr::block("display_block", gr::io_signature::make(0, 0, 0),
                    gr::io_signature::make(0, 0, 0)),
          d_logger(new gr::logger("map_display_logger")) {
        message_port_register_in(pmt::mp("in"));
        set_msg_handler(pmt::mp("in"),
                        [this](pmt::pmt_t msg) { handle_msg(msg); });
    }

    void handle_msg(pmt::pmt_t msg) {
        if (!pmt::is_dict(msg)) {
            GR_LOG_WARN(d_logger, "Not a PMT dict");
            return;
        }

        pmt::pmt_t lat = pmt::dict_ref(msg, pmt::intern("lat"), pmt::PMT_NIL);
        pmt::pmt_t lon = pmt::dict_ref(msg, pmt::intern("lon"), pmt::PMT_NIL);
        if (pmt::is_real(lat) && pmt::is_real(lon)) {
            double latitude = pmt::to_double(lat);
            double longitude = pmt::to_double(lon);
            GR_LOG_INFO(d_logger, "Got coordinates " +
                                      std::to_string(latitude) + ", " +
                                      std::to_string(longitude));
        }
    }
};

display_block::sptr display_block::make() {
    return std::make_shared<display_block_impl>();
}

}  // namespace map_display
}  // namespace gr
