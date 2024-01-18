// Low level image processing implemented in C++ for good performance.
#ifndef CONVERSION_H
#define CONVERSION_H


extern "C" {
    __declspec(dllexport) void set_cubemap(
        char* input, int input_width, int input_height,
        char* output, bool* cancel);
    __declspec(dllexport) void project(
        char* output, int output_width, int output_height,
        double pitch, double yaw, double fov, char* cubemap, int face_length);
}


// Cube faces.
enum Faces {FRONT, BACK, TOP, BOTTOM, RIGHT, LEFT};


void set_cubemap(char* input, int w, int h, char* output, bool* cancel);
void project(
    char* output, int output_width, int output_height,
    double pitch, double yaw, double fov, char* cubemap, int face_length
);


#endif
