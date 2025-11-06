#pragma once

#include "map_display/display_block.h"

namespace gr {
namespace map_display {

class multDivSelect_impl : public display_block {
   private:
    // Nothing to declare in this block.

   public:
    multDivSelect_impl(bool selector);
    ~multDivSelect_impl();

    // Where all the action really happens
    int work(int noutput_items, gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);
};

}  // namespace map_display
}  // namespace gr
