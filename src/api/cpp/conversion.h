// Low level image processing implemented in C++ for good performance.
#ifndef CONVERSION_H
#define CONVERSION_H


extern "C" {
    __declspec(dllexport) void set_cubemap(
        char* input, int input_width, int input_height, char* output);
}


// Cube faces.
enum Faces {FRONT, BACK, TOP, BOTTOM, RIGHT, LEFT};


void set_cubemap(char* input, int w, int h, char* output);
void project(
    char* input, int input_width, int input_height,
    char* output, int output_width, int output_height,
    double pitch, double yaw, double fov, char* cubemap = nullptr
);
void set_pixel_colour(
    char* input, char* r, int width, int height, int face_x, int face_y,
    Faces face
);

#endif
