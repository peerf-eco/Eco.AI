#ifndef GGUF_ORIGINAL_H
#define GGUF_ORIGINAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define GGUF_FORMAT_NAME "GGUF"
#define GGUF_MAGIC 0x46554747u
#define GGUF_VERSION 3u
#define GGUF_DEFAULT_ALIGNMENT 32u

typedef enum ggml_type {
    GGML_TYPE_F32     = 0,
    GGML_TYPE_F16     = 1,
    GGML_TYPE_Q4_0    = 2,
    GGML_TYPE_Q4_1    = 3,
    GGML_TYPE_Q5_0    = 6,
    GGML_TYPE_Q5_1    = 7,
    GGML_TYPE_Q8_0    = 8,
    GGML_TYPE_Q8_1    = 9,
    GGML_TYPE_Q2_K    = 10,
    GGML_TYPE_Q3_K    = 11,
    GGML_TYPE_Q4_K    = 12,
    GGML_TYPE_Q5_K    = 13,
    GGML_TYPE_Q6_K    = 14,
    GGML_TYPE_Q8_K    = 15,
    GGML_TYPE_IQ2_XXS = 16,
    GGML_TYPE_IQ2_XS  = 17,
    GGML_TYPE_IQ3_XXS = 18,
    GGML_TYPE_IQ1_S   = 19,
    GGML_TYPE_IQ4_NL  = 20,
    GGML_TYPE_IQ3_S   = 21,
    GGML_TYPE_IQ2_S   = 22,
    GGML_TYPE_IQ4_XS  = 23,
    GGML_TYPE_I8      = 24,
    GGML_TYPE_I16     = 25,
    GGML_TYPE_I32     = 26,
    GGML_TYPE_I64     = 27,
    GGML_TYPE_F64     = 28,
    GGML_TYPE_IQ1_M   = 29,
    GGML_TYPE_BF16    = 30,
    GGML_TYPE_TQ1_0   = 34,
    GGML_TYPE_TQ2_0   = 35,
    GGML_TYPE_MXFP4   = 39,
    GGML_TYPE_COUNT   = 40
} ggml_type;

typedef enum gguf_metadata_value_type {
    GGUF_METADATA_VALUE_TYPE_UINT8   = 0,
    GGUF_METADATA_VALUE_TYPE_INT8    = 1,
    GGUF_METADATA_VALUE_TYPE_UINT16  = 2,
    GGUF_METADATA_VALUE_TYPE_INT16   = 3,
    GGUF_METADATA_VALUE_TYPE_UINT32  = 4,
    GGUF_METADATA_VALUE_TYPE_INT32   = 5,
    GGUF_METADATA_VALUE_TYPE_FLOAT32 = 6,
    GGUF_METADATA_VALUE_TYPE_BOOL    = 7,
    GGUF_METADATA_VALUE_TYPE_STRING  = 8,
    GGUF_METADATA_VALUE_TYPE_ARRAY   = 9,
    GGUF_METADATA_VALUE_TYPE_UINT64  = 10,
    GGUF_METADATA_VALUE_TYPE_INT64   = 11,
    GGUF_METADATA_VALUE_TYPE_FLOAT64 = 12
} gguf_metadata_value_type;

typedef enum gguf_status {
    GGUF_STATUS_OK = 0,
    GGUF_STATUS_INVALID_ARGUMENT = 1,
    GGUF_STATUS_IO_ERROR = 2,
    GGUF_STATUS_INVALID_MAGIC = 3,
    GGUF_STATUS_UNSUPPORTED_VERSION = 4,
    GGUF_STATUS_INVALID_FORMAT = 5,
    GGUF_STATUS_OUT_OF_MEMORY = 6,
    GGUF_STATUS_NOT_IMPLEMENTED = 7
} gguf_status;

typedef struct gguf_string_t {
    uint64_t len;
    char *string;
} gguf_string_t;

struct gguf_metadata_value_t;

typedef struct gguf_metadata_array_t {
    uint32_t type;
    uint64_t len;
    struct gguf_metadata_value_t *items;
} gguf_metadata_array_t;

typedef struct gguf_metadata_value_t {
    uint32_t type;
    union {
        uint8_t uint8;
        int8_t int8;
        uint16_t uint16;
        int16_t int16;
        uint32_t uint32;
        int32_t int32;
        float float32;
        uint64_t uint64;
        int64_t int64;
        double float64;
        bool bool_;
        gguf_string_t string;
        gguf_metadata_array_t array;
    } value;
} gguf_metadata_value_t;

typedef struct gguf_metadata_kv_t {
    gguf_string_t key;
    uint32_t value_type;
    gguf_metadata_value_t value;
} gguf_metadata_kv_t;

typedef struct gguf_header_t {
    uint32_t magic;
    uint32_t version;
    uint64_t tensor_count;
    uint64_t metadata_kv_count;
} gguf_header_t;

typedef struct gguf_tensor_info_t {
    gguf_string_t name;
    uint32_t n_dimensions;
    uint64_t *dimensions;
    uint32_t type;
    uint64_t offset;
    uint64_t size;
    uint64_t file_offset;
    const uint8_t *data;
} gguf_tensor_info_t;

typedef struct gguf_tensor_section_t {
    const char *name;
    uint64_t name_len;
    uint64_t offset;
    uint64_t file_offset;
    uint64_t size;
    const uint8_t *data;
} gguf_tensor_section_t;

typedef struct gguf_file_t {
    gguf_header_t header;
    uint32_t alignment;
    uint64_t tensor_data_offset;
    gguf_metadata_kv_t *metadata_kv;
    gguf_tensor_info_t *tensor_infos;
    gguf_tensor_section_t *tensor_sections;
    uint8_t *tensor_data;
    uint64_t tensor_data_size;
    char *tensor_data_source_path;
    uint64_t tensor_data_source_offset;
    uint64_t tensor_data_source_size;
} gguf_file_t;

uint64_t gguf_align_offset(uint64_t offset, uint32_t alignment);
const char *gguf_status_string(gguf_status status);
const char *gguf_ggml_type_name(uint32_t type);
const char *gguf_metadata_type_name(uint32_t type);
const gguf_metadata_kv_t *gguf_find_metadata(const gguf_file_t *file, const char *key);
void gguf_free(gguf_file_t *file);
gguf_status gguf_load_file(const char *path, gguf_file_t *out_file, char *error, size_t error_size);
gguf_status gguf_load_memory(const void *data, uint64_t size, gguf_file_t *out_file, char *error, size_t error_size);
gguf_status gguf_save_file(const char *path, const gguf_file_t *file, char *error, size_t error_size);
gguf_status gguf_serialize_to_memory(const gguf_file_t *file, uint8_t **data, uint64_t *size, char *error, size_t error_size);
void gguf_print_summary(const gguf_file_t *file, FILE *stream);

#endif /* GGUF_ORIGINAL_H */
