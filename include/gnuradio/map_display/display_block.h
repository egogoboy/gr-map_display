#pragma once

#include <gnuradio/block.h>

#include <cmath>

namespace gr {
namespace map_display {

class display_block : virtual public gr::block {
   public:
    typedef std::shared_ptr<display_block> sptr;

    // Factory method to create new instance
    static sptr make();
};

}  // namespace map_display
}  // namespace gr
