set(GRC_INSTALL_DIR /usr/share/gnuradio/grc/blocks)
set(GNURADIO_PYTHON_DIR /usr/lib/python3/dist-packages)

cmake_minimum_required(VERSION 3.8)
project(gr-map_display)

find_package(Gnuradio REQUIRED COMPONENTS grc)

message(STATUS "GRC install dir: ${Gnuradio_GRC_INSTALL_DIR}")
message(STATUS "Python dir: ${Gnuradio_PYTHON_DIR}")

add_subdirectory(python)

install(
    FILES ${CMAKE_CURRENT_SOURCE_DIR}/python/map_display/assets/mok_map.png
    DESTINATION /usr/lib/python3/dist-packages/map_display/assets
)

install (
    FILES grc/map_display_map_drawer.block.yml
    DESTINATION /usr/share/gnuradio/grc/blocks
)
