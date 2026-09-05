#include "gguf.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void print_usage(const char *program_name) {
    fprintf(stderr, "Usage: %s <input.gguf> [output.gguf]\n", program_name);
    fprintf(stderr, "       %s --help\n", program_name);
}

int main(int argc, char **argv) {
    gguf_file_t input_file;
    gguf_file_t output_file;
    gguf_status status = GGUF_STATUS_OK;
    char error[1024];

    if (argc < 2 || argc > 3) {
        print_usage(argc > 0 ? argv[0] : "gguf_cli");
        return 1;
    }

    if (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0) {
        print_usage(argv[0]);
        return 0;
    }

    memset(&input_file, 0, sizeof(input_file));
    memset(&output_file, 0, sizeof(output_file));
    memset(error, 0, sizeof(error));

    status = gguf_load_file(argv[1], &input_file, error, sizeof(error));
    if (status != GGUF_STATUS_OK) {
        fprintf(stderr, "load failed: %s\n", error[0] == '\0' ? gguf_status_string(status) : error);
        return 2;
    }

    printf("input_file: %s\n", argv[1]);
    gguf_print_summary(&input_file, stdout);

    if (argc == 3) {
        memset(error, 0, sizeof(error));
        status = gguf_save_file(argv[2], &input_file, error, sizeof(error));
        if (status != GGUF_STATUS_OK) {
            fprintf(stderr, "save failed: %s\n", error[0] == '\0' ? gguf_status_string(status) : error);
            gguf_free(&input_file);
            return 3;
        }

        memset(error, 0, sizeof(error));
        status = gguf_load_file(argv[2], &output_file, error, sizeof(error));
        if (status != GGUF_STATUS_OK) {
            fprintf(stderr, "reload failed: %s\n", error[0] == '\0' ? gguf_status_string(status) : error);
            gguf_free(&input_file);
            return 4;
        }

        printf("output_file: %s\n", argv[2]);
        gguf_print_summary(&output_file, stdout);
        gguf_free(&output_file);
    }

    gguf_free(&input_file);
    return 0;
}
