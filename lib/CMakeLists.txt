# Создаём библиотеку
add_library(gnuradio-map_display SHARED
    map_display_impl.cc
)

# Пути include для сборки и LSP
target_include_directories(gnuradio-map_display
    PUBLIC
        ${CMAKE_SOURCE_DIR}/include        # твои хедеры
        /opt/homebrew/opt/gnuradio/include
        /opt/homebrew/opt/gnuradio/include/gnuradio
        /opt/homebrew/opt/gnuradio/include/pmt
)

# Линковка с GNU Radio и Boost
target_link_libraries(gnuradio-map_display
    PUBLIC
        gnuradio-runtime
        gnuradio-blocks
        ${Boost_LIBRARIES}
)

# Свойства библиотеки
set_target_properties(gnuradio-map_display PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
    OUTPUT_NAME "gnuradio-map_display"
)

# Установка библиотеки
install(TARGETS gnuradio-map_display
    DESTINATION lib
)
