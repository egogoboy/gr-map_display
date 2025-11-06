cmake_minimum_required(VERSION 3.16)
project(gr-map_display LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Пути к GNU Radio (Homebrew)
list(APPEND CMAKE_PREFIX_PATH "/opt/homebrew/opt/gnuradio")

# Найти GNU Radio
find_package(Gnuradio REQUIRED)

# Найти Boost
find_package(Boost REQUIRED COMPONENTS thread program_options)

# Включаем папку include для LSP и сборки
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Добавляем библиотеку
add_subdirectory(lib)

# Установка хедеров
install(
    DIRECTORY include/gnuradio/map_display
    DESTINATION include/gnuradio/map_display
    FILES_MATCHING PATTERN "*.h"
)
