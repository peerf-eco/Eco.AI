#include "gguf.h"

#include <errno.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <stdio.h>
#include <windows.h>
#else
#include <sys/stat.h>
#endif

typedef struct gguf_reader_t {
    const uint8_t *data;
    uint64_t size;
    uint64_t pos;
    char *error;
    size_t error_size;
} gguf_reader_t;

typedef struct gguf_writer_t {
    FILE *file;
    uint8_t *buffer;
    uint64_t capacity;
    int mode;
    uint64_t pos;
    char *error;
    size_t error_size;
} gguf_writer_t;

#define GGUF_WRITER_MODE_FILE   1
#define GGUF_WRITER_MODE_BUFFER 2
#define GGUF_WRITER_MODE_COUNT  3

static int gguf_fseek64(FILE *file, int64_t offset, int origin);
static int64_t gguf_ftell64(FILE *file);

static int gguf_paths_refer_to_same_file(const char *left, const char *right);

static void gguf_set_error(char *error, size_t error_size, const char *fmt, ...) {
    va_list args;

    if (error == NULL || error_size == 0) {
        return;
    }

    va_start(args, fmt);
    vsnprintf(error, error_size, fmt, args);
    va_end(args);
}

static int gguf_mul_overflow_size(size_t a, size_t b, size_t *result) {
    if (a == 0 || b == 0) {
        *result = 0;
        return 0;
    }

    if (a > ((size_t)-1) / b) {
        return 1;
    }

    *result = a * b;
    return 0;
}

static void *gguf_calloc_items(size_t count, size_t size) {
    size_t total = 0;

    if (gguf_mul_overflow_size(count, size, &total)) {
        return NULL;
    }

    return calloc(1, total);
}

static char *gguf_strdup_string(const char *value) {
    size_t len = 0;
    char *copy = NULL;

    if (value == NULL) {
        return NULL;
    }

    len = strlen(value);
    copy = (char *)malloc(len + 1u);
    if (copy == NULL) {
        return NULL;
    }

    memcpy(copy, value, len + 1u);
    return copy;
}

static uint16_t gguf_read_u16_le(const uint8_t *ptr) {
    return (uint16_t)ptr[0] | ((uint16_t)ptr[1] << 8);
}

static int16_t gguf_read_i16_le(const uint8_t *ptr) {
    return (int16_t)gguf_read_u16_le(ptr);
}

static uint32_t gguf_read_u32_le(const uint8_t *ptr) {
    return (uint32_t)ptr[0] |
           ((uint32_t)ptr[1] << 8) |
           ((uint32_t)ptr[2] << 16) |
           ((uint32_t)ptr[3] << 24);
}

static int32_t gguf_read_i32_le(const uint8_t *ptr) {
    return (int32_t)gguf_read_u32_le(ptr);
}

static uint64_t gguf_read_u64_le(const uint8_t *ptr) {
    return (uint64_t)ptr[0] |
           ((uint64_t)ptr[1] << 8) |
           ((uint64_t)ptr[2] << 16) |
           ((uint64_t)ptr[3] << 24) |
           ((uint64_t)ptr[4] << 32) |
           ((uint64_t)ptr[5] << 40) |
           ((uint64_t)ptr[6] << 48) |
           ((uint64_t)ptr[7] << 56);
}

static int64_t gguf_read_i64_le(const uint8_t *ptr) {
    return (int64_t)gguf_read_u64_le(ptr);
}

static float gguf_read_f32_le(const uint8_t *ptr) {
    union {
        uint32_t u32;
        float f32;
    } value;

    value.u32 = gguf_read_u32_le(ptr);
    return value.f32;
}

static double gguf_read_f64_le(const uint8_t *ptr) {
    union {
        uint64_t u64;
        double f64;
    } value;

    value.u64 = gguf_read_u64_le(ptr);
    return value.f64;
}

static void gguf_write_u16_le(uint8_t *ptr, uint16_t value) {
    ptr[0] = (uint8_t)(value & 0xFFu);
    ptr[1] = (uint8_t)((value >> 8) & 0xFFu);
}

static void gguf_write_u32_le(uint8_t *ptr, uint32_t value) {
    ptr[0] = (uint8_t)(value & 0xFFu);
    ptr[1] = (uint8_t)((value >> 8) & 0xFFu);
    ptr[2] = (uint8_t)((value >> 16) & 0xFFu);
    ptr[3] = (uint8_t)((value >> 24) & 0xFFu);
}

static void gguf_write_u64_le(uint8_t *ptr, uint64_t value) {
    ptr[0] = (uint8_t)(value & 0xFFu);
    ptr[1] = (uint8_t)((value >> 8) & 0xFFu);
    ptr[2] = (uint8_t)((value >> 16) & 0xFFu);
    ptr[3] = (uint8_t)((value >> 24) & 0xFFu);
    ptr[4] = (uint8_t)((value >> 32) & 0xFFu);
    ptr[5] = (uint8_t)((value >> 40) & 0xFFu);
    ptr[6] = (uint8_t)((value >> 48) & 0xFFu);
    ptr[7] = (uint8_t)((value >> 56) & 0xFFu);
}

static void gguf_write_f32_le(uint8_t *ptr, float value) {
    union {
        uint32_t u32;
        float f32;
    } data;

    data.f32 = value;
    gguf_write_u32_le(ptr, data.u32);
}

static void gguf_write_f64_le(uint8_t *ptr, double value) {
    union {
        uint64_t u64;
        double f64;
    } data;

    data.f64 = value;
    gguf_write_u64_le(ptr, data.u64);
}

static int gguf_writer_write_bytes(gguf_writer_t *writer, const void *src, size_t bytes) {
    if (bytes == 0) {
        return 1;
    }

    if (writer->mode == GGUF_WRITER_MODE_FILE) {
        if (fwrite(src, 1, bytes, writer->file) != bytes) {
            gguf_set_error(writer->error, writer->error_size, "Unable to write output file");
            return 0;
        }
    }
    else if (writer->mode == GGUF_WRITER_MODE_BUFFER) {
        if (writer->pos > writer->capacity || (uint64_t)bytes > (writer->capacity - writer->pos)) {
            gguf_set_error(writer->error, writer->error_size, "Serialization buffer is too small");
            return 0;
        }
        memcpy(writer->buffer + writer->pos, src, bytes);
    }
    else if (writer->mode != GGUF_WRITER_MODE_COUNT) {
        gguf_set_error(writer->error, writer->error_size, "Invalid writer mode");
        return 0;
    }

    writer->pos += (uint64_t)bytes;
    return 1;
}

static int gguf_writer_write_u8(gguf_writer_t *writer, uint8_t value) {
    return gguf_writer_write_bytes(writer, &value, sizeof(value));
}

static int gguf_writer_write_u16(gguf_writer_t *writer, uint16_t value) {
    uint8_t bytes[2];

    gguf_write_u16_le(bytes, value);
    return gguf_writer_write_bytes(writer, bytes, sizeof(bytes));
}

static int gguf_writer_write_i16(gguf_writer_t *writer, int16_t value) {
    return gguf_writer_write_u16(writer, (uint16_t)value);
}

static int gguf_writer_write_u32(gguf_writer_t *writer, uint32_t value) {
    uint8_t bytes[4];

    gguf_write_u32_le(bytes, value);
    return gguf_writer_write_bytes(writer, bytes, sizeof(bytes));
}

static int gguf_writer_write_i32(gguf_writer_t *writer, int32_t value) {
    return gguf_writer_write_u32(writer, (uint32_t)value);
}

static int gguf_writer_write_u64(gguf_writer_t *writer, uint64_t value) {
    uint8_t bytes[8];

    gguf_write_u64_le(bytes, value);
    return gguf_writer_write_bytes(writer, bytes, sizeof(bytes));
}

static int gguf_writer_write_i64(gguf_writer_t *writer, int64_t value) {
    return gguf_writer_write_u64(writer, (uint64_t)value);
}

static int gguf_writer_write_f32(gguf_writer_t *writer, float value) {
    uint8_t bytes[4];

    gguf_write_f32_le(bytes, value);
    return gguf_writer_write_bytes(writer, bytes, sizeof(bytes));
}

static int gguf_writer_write_f64(gguf_writer_t *writer, double value) {
    uint8_t bytes[8];

    gguf_write_f64_le(bytes, value);
    return gguf_writer_write_bytes(writer, bytes, sizeof(bytes));
}

static int gguf_reader_can_read(gguf_reader_t *reader, uint64_t bytes) {
    return reader->pos <= reader->size && bytes <= (reader->size - reader->pos);
}

static int gguf_reader_read_bytes(gguf_reader_t *reader, void *dst, uint64_t bytes) {
    if (!gguf_reader_can_read(reader, bytes)) {
        gguf_set_error(reader->error, reader->error_size, "Unexpected end of file at byte %" PRIu64, reader->pos);
        return 0;
    }

    if (bytes != 0 && dst != NULL) {
        memcpy(dst, reader->data + reader->pos, (size_t)bytes);
    }

    reader->pos += bytes;
    return 1;
}

static int gguf_reader_read_u8(gguf_reader_t *reader, uint8_t *value) {
    return gguf_reader_read_bytes(reader, value, 1);
}

static int gguf_reader_read_i8(gguf_reader_t *reader, int8_t *value) {
    return gguf_reader_read_bytes(reader, value, 1);
}

static int gguf_reader_read_u16(gguf_reader_t *reader, uint16_t *value) {
    uint8_t bytes[2];

    if (!gguf_reader_read_bytes(reader, bytes, sizeof(bytes))) {
        return 0;
    }

    *value = gguf_read_u16_le(bytes);
    return 1;
}

static int gguf_reader_read_i16(gguf_reader_t *reader, int16_t *value) {
    uint8_t bytes[2];

    if (!gguf_reader_read_bytes(reader, bytes, sizeof(bytes))) {
        return 0;
    }

    *value = gguf_read_i16_le(bytes);
    return 1;
}

static int gguf_reader_read_u32(gguf_reader_t *reader, uint32_t *value) {
    uint8_t bytes[4];

    if (!gguf_reader_read_bytes(reader, bytes, sizeof(bytes))) {
        return 0;
    }

    *value = gguf_read_u32_le(bytes);
    return 1;
}

static int gguf_reader_read_i32(gguf_reader_t *reader, int32_t *value) {
    uint8_t bytes[4];

    if (!gguf_reader_read_bytes(reader, bytes, sizeof(bytes))) {
        return 0;
    }

    *value = gguf_read_i32_le(bytes);
    return 1;
}

static int gguf_reader_read_u64(gguf_reader_t *reader, uint64_t *value) {
    uint8_t bytes[8];

    if (!gguf_reader_read_bytes(reader, bytes, sizeof(bytes))) {
        return 0;
    }

    *value = gguf_read_u64_le(bytes);
    return 1;
}

static int gguf_reader_read_i64(gguf_reader_t *reader, int64_t *value) {
    uint8_t bytes[8];

    if (!gguf_reader_read_bytes(reader, bytes, sizeof(bytes))) {
        return 0;
    }

    *value = gguf_read_i64_le(bytes);
    return 1;
}

static int gguf_reader_read_f32(gguf_reader_t *reader, float *value) {
    uint8_t bytes[4];

    if (!gguf_reader_read_bytes(reader, bytes, sizeof(bytes))) {
        return 0;
    }

    *value = gguf_read_f32_le(bytes);
    return 1;
}

static int gguf_reader_read_f64(gguf_reader_t *reader, double *value) {
    uint8_t bytes[8];

    if (!gguf_reader_read_bytes(reader, bytes, sizeof(bytes))) {
        return 0;
    }

    *value = gguf_read_f64_le(bytes);
    return 1;
}

static void gguf_free_string(gguf_string_t *string) {
    if (string == NULL) {
        return;
    }

    free(string->string);
    string->string = NULL;
    string->len = 0;
}

static int gguf_reader_read_string(gguf_reader_t *reader, gguf_string_t *string) {
    if (!gguf_reader_read_u64(reader, &string->len)) {
        return 0;
    }

    if (string->len > (uint64_t)((size_t)-1) - 1u) {
        gguf_set_error(reader->error, reader->error_size, "String is too large to allocate");
        return 0;
    }

    string->string = (char *)malloc((size_t)string->len + 1u);
    if (string->string == NULL) {
        gguf_set_error(reader->error, reader->error_size, "Out of memory allocating string");
        return 0;
    }

    if (!gguf_reader_read_bytes(reader, string->string, string->len)) {
        gguf_free_string(string);
        return 0;
    }

    string->string[string->len] = '\0';
    return 1;
}

static void gguf_free_metadata_value(gguf_metadata_value_t *value) {
    uint64_t index = 0;

    if (value == NULL) {
        return;
    }

    if (value->type == GGUF_METADATA_VALUE_TYPE_STRING) {
        gguf_free_string(&value->value.string);
    }
    else if (value->type == GGUF_METADATA_VALUE_TYPE_ARRAY) {
        for (index = 0; index < value->value.array.len; ++index) {
            gguf_free_metadata_value(&value->value.array.items[index]);
        }
        free(value->value.array.items);
        value->value.array.items = NULL;
        value->value.array.len = 0;
    }
}

static int gguf_reader_read_metadata_value(gguf_reader_t *reader, uint32_t type, gguf_metadata_value_t *value) {
    uint64_t index = 0;

    memset(value, 0, sizeof(*value));
    value->type = type;

    switch (type) {
        case GGUF_METADATA_VALUE_TYPE_UINT8:
            return gguf_reader_read_u8(reader, &value->value.uint8);
        case GGUF_METADATA_VALUE_TYPE_INT8:
            return gguf_reader_read_i8(reader, &value->value.int8);
        case GGUF_METADATA_VALUE_TYPE_UINT16:
            return gguf_reader_read_u16(reader, &value->value.uint16);
        case GGUF_METADATA_VALUE_TYPE_INT16:
            return gguf_reader_read_i16(reader, &value->value.int16);
        case GGUF_METADATA_VALUE_TYPE_UINT32:
            return gguf_reader_read_u32(reader, &value->value.uint32);
        case GGUF_METADATA_VALUE_TYPE_INT32:
            return gguf_reader_read_i32(reader, &value->value.int32);
        case GGUF_METADATA_VALUE_TYPE_FLOAT32:
            return gguf_reader_read_f32(reader, &value->value.float32);
        case GGUF_METADATA_VALUE_TYPE_BOOL: {
            uint8_t bool_value = 0;
            if (!gguf_reader_read_u8(reader, &bool_value)) {
                return 0;
            }
            if (bool_value > 1u) {
                gguf_set_error(reader->error, reader->error_size, "Invalid boolean value %u", (unsigned)bool_value);
                return 0;
            }
            value->value.bool_ = bool_value != 0;
            return 1;
        }
        case GGUF_METADATA_VALUE_TYPE_STRING:
            return gguf_reader_read_string(reader, &value->value.string);
        case GGUF_METADATA_VALUE_TYPE_ARRAY:
            if (!gguf_reader_read_u32(reader, &value->value.array.type)) {
                return 0;
            }
            if (!gguf_reader_read_u64(reader, &value->value.array.len)) {
                return 0;
            }
            if (value->value.array.len == 0) {
                value->value.array.items = NULL;
                return 1;
            }
            if (value->value.array.len > (uint64_t)((size_t)-1) / sizeof(gguf_metadata_value_t)) {
                gguf_set_error(reader->error, reader->error_size, "Metadata array is too large to allocate");
                return 0;
            }
            value->value.array.items = (gguf_metadata_value_t *)gguf_calloc_items((size_t)value->value.array.len, sizeof(gguf_metadata_value_t));
            if (value->value.array.items == NULL) {
                gguf_set_error(reader->error, reader->error_size, "Out of memory allocating metadata array");
                return 0;
            }
            for (index = 0; index < value->value.array.len; ++index) {
                if (!gguf_reader_read_metadata_value(reader, value->value.array.type, &value->value.array.items[index])) {
                    return 0;
                }
            }
            return 1;
        case GGUF_METADATA_VALUE_TYPE_UINT64:
            return gguf_reader_read_u64(reader, &value->value.uint64);
        case GGUF_METADATA_VALUE_TYPE_INT64:
            return gguf_reader_read_i64(reader, &value->value.int64);
        case GGUF_METADATA_VALUE_TYPE_FLOAT64:
            return gguf_reader_read_f64(reader, &value->value.float64);
        default:
            gguf_set_error(reader->error, reader->error_size, "Unsupported metadata value type %u", type);
            return 0;
    }
}

static void gguf_free_metadata_kv(gguf_metadata_kv_t *kv) {
    if (kv == NULL) {
        return;
    }

    gguf_free_string(&kv->key);
    gguf_free_metadata_value(&kv->value);
}

static int gguf_reader_read_metadata_kv(gguf_reader_t *reader, gguf_metadata_kv_t *kv) {
    memset(kv, 0, sizeof(*kv));

    if (!gguf_reader_read_string(reader, &kv->key)) {
        return 0;
    }

    if (!gguf_reader_read_u32(reader, &kv->value_type)) {
        gguf_free_string(&kv->key);
        return 0;
    }

    if (!gguf_reader_read_metadata_value(reader, kv->value_type, &kv->value)) {
        gguf_free_string(&kv->key);
        return 0;
    }

    return 1;
}

static void gguf_free_tensor_info(gguf_tensor_info_t *tensor) {
    if (tensor == NULL) {
        return;
    }

    gguf_free_string(&tensor->name);
    free(tensor->dimensions);
    tensor->dimensions = NULL;
    tensor->n_dimensions = 0;
}

static int gguf_reader_read_tensor_info(gguf_reader_t *reader, gguf_tensor_info_t *tensor) {
    memset(tensor, 0, sizeof(*tensor));

    if (!gguf_reader_read_string(reader, &tensor->name)) {
        return 0;
    }

    if (tensor->name.len > 64u) {
        gguf_set_error(reader->error, reader->error_size, "Tensor name exceeds 64 bytes: %s", tensor->name.string);
        gguf_free_string(&tensor->name);
        return 0;
    }

    if (!gguf_reader_read_u32(reader, &tensor->n_dimensions)) {
        gguf_free_string(&tensor->name);
        return 0;
    }

    if (tensor->n_dimensions != 0) {
        if (tensor->n_dimensions > (uint32_t)((size_t)-1) / sizeof(uint64_t)) {
            gguf_set_error(reader->error, reader->error_size, "Too many tensor dimensions");
            gguf_free_string(&tensor->name);
            return 0;
        }
        tensor->dimensions = (uint64_t *)gguf_calloc_items((size_t)tensor->n_dimensions, sizeof(uint64_t));
        if (tensor->dimensions == NULL) {
            gguf_set_error(reader->error, reader->error_size, "Out of memory allocating tensor dimensions");
            gguf_free_string(&tensor->name);
            return 0;
        }
    }

    for (uint32_t index = 0; index < tensor->n_dimensions; ++index) {
        if (!gguf_reader_read_u64(reader, &tensor->dimensions[index])) {
            gguf_free_tensor_info(tensor);
            return 0;
        }
    }

    if (!gguf_reader_read_u32(reader, &tensor->type) ||
        !gguf_reader_read_u64(reader, &tensor->offset)) {
        gguf_free_tensor_info(tensor);
        return 0;
    }

    return 1;
}

static const gguf_metadata_kv_t *gguf_find_metadata_internal(const gguf_file_t *file, const char *key) {
    uint64_t index = 0;

    if (file == NULL || key == NULL) {
        return NULL;
    }

    for (index = 0; index < file->header.metadata_kv_count; ++index) {
        if (file->metadata_kv[index].key.string != NULL &&
            strcmp(file->metadata_kv[index].key.string, key) == 0) {
            return &file->metadata_kv[index];
        }
    }

    return NULL;
}

static uint32_t gguf_detect_alignment(const gguf_file_t *file) {
    const gguf_metadata_kv_t *kv = gguf_find_metadata_internal(file, "general.alignment");

    if (kv == NULL) {
        return GGUF_DEFAULT_ALIGNMENT;
    }

    switch (kv->value_type) {
        case GGUF_METADATA_VALUE_TYPE_UINT32:
            return kv->value.value.uint32 == 0 ? GGUF_DEFAULT_ALIGNMENT : kv->value.value.uint32;
        case GGUF_METADATA_VALUE_TYPE_UINT64:
            return kv->value.value.uint64 == 0 ? GGUF_DEFAULT_ALIGNMENT : (uint32_t)kv->value.value.uint64;
        case GGUF_METADATA_VALUE_TYPE_INT32:
            return kv->value.value.int32 <= 0 ? GGUF_DEFAULT_ALIGNMENT : (uint32_t)kv->value.value.int32;
        case GGUF_METADATA_VALUE_TYPE_INT64:
            return kv->value.value.int64 <= 0 ? GGUF_DEFAULT_ALIGNMENT : (uint32_t)kv->value.value.int64;
        default:
            return GGUF_DEFAULT_ALIGNMENT;
    }
}

typedef struct gguf_sorted_tensor_t {
    uint64_t index;
    uint64_t offset;
    uint64_t end;
} gguf_sorted_tensor_t;

static int gguf_compare_sorted_tensors(const void *left, const void *right) {
    const gguf_sorted_tensor_t *lhs = (const gguf_sorted_tensor_t *)left;
    const gguf_sorted_tensor_t *rhs = (const gguf_sorted_tensor_t *)right;

    if (lhs->offset < rhs->offset) {
        return -1;
    }
    if (lhs->offset > rhs->offset) {
        return 1;
    }
    if (lhs->index < rhs->index) {
        return -1;
    }
    if (lhs->index > rhs->index) {
        return 1;
    }

    return 0;
}

static int gguf_mul_overflow_u64(uint64_t a, uint64_t b, uint64_t *result) {
    if (a == 0 || b == 0) {
        *result = 0;
        return 0;
    }

    if (a > UINT64_MAX / b) {
        return 1;
    }

    *result = a * b;
    return 0;
}

static int gguf_add_overflow_u64(uint64_t a, uint64_t b, uint64_t *result) {
    if (a > UINT64_MAX - b) {
        return 1;
    }

    *result = a + b;
    return 0;
}

static int gguf_type_block_size(uint32_t type, uint64_t *block_size, uint64_t *type_size) {
    if (block_size == NULL || type_size == NULL) {
        return 0;
    }

    switch (type) {
        case GGML_TYPE_F32:     *block_size = 1u;   *type_size = 4u;   return 1;
        case GGML_TYPE_F16:     *block_size = 1u;   *type_size = 2u;   return 1;
        case GGML_TYPE_Q4_0:    *block_size = 32u;  *type_size = 18u;  return 1;
        case GGML_TYPE_Q4_1:    *block_size = 32u;  *type_size = 20u;  return 1;
        case GGML_TYPE_Q5_0:    *block_size = 32u;  *type_size = 22u;  return 1;
        case GGML_TYPE_Q5_1:    *block_size = 32u;  *type_size = 24u;  return 1;
        case GGML_TYPE_Q8_0:    *block_size = 32u;  *type_size = 34u;  return 1;
        case GGML_TYPE_Q8_1:    *block_size = 32u;  *type_size = 40u;  return 1;
        case GGML_TYPE_Q2_K:    *block_size = 256u; *type_size = 84u;  return 1;
        case GGML_TYPE_Q3_K:    *block_size = 256u; *type_size = 110u; return 1;
        case GGML_TYPE_Q4_K:    *block_size = 256u; *type_size = 144u; return 1;
        case GGML_TYPE_Q5_K:    *block_size = 256u; *type_size = 176u; return 1;
        case GGML_TYPE_Q6_K:    *block_size = 256u; *type_size = 210u; return 1;
        case GGML_TYPE_Q8_K:    *block_size = 256u; *type_size = 292u; return 1;
        case GGML_TYPE_IQ2_XXS: *block_size = 256u; *type_size = 66u;  return 1;
        case GGML_TYPE_IQ2_XS:  *block_size = 256u; *type_size = 74u;  return 1;
        case GGML_TYPE_IQ3_XXS: *block_size = 256u; *type_size = 98u;  return 1;
        case GGML_TYPE_IQ1_S:   *block_size = 256u; *type_size = 50u;  return 1;
        case GGML_TYPE_IQ4_NL:  *block_size = 32u;  *type_size = 18u;  return 1;
        case GGML_TYPE_IQ3_S:   *block_size = 256u; *type_size = 110u; return 1;
        case GGML_TYPE_IQ2_S:   *block_size = 256u; *type_size = 82u;  return 1;
        case GGML_TYPE_IQ4_XS:  *block_size = 256u; *type_size = 136u; return 1;
        case GGML_TYPE_I8:      *block_size = 1u;   *type_size = 1u;   return 1;
        case GGML_TYPE_I16:     *block_size = 1u;   *type_size = 2u;   return 1;
        case GGML_TYPE_I32:     *block_size = 1u;   *type_size = 4u;   return 1;
        case GGML_TYPE_I64:     *block_size = 1u;   *type_size = 8u;   return 1;
        case GGML_TYPE_F64:     *block_size = 1u;   *type_size = 8u;   return 1;
        case GGML_TYPE_IQ1_M:   *block_size = 256u; *type_size = 56u;  return 1;
        case GGML_TYPE_BF16:    *block_size = 1u;   *type_size = 2u;   return 1;
        case GGML_TYPE_TQ1_0:   *block_size = 256u; *type_size = 54u;  return 1;
        case GGML_TYPE_TQ2_0:   *block_size = 256u; *type_size = 66u;  return 1;
        case GGML_TYPE_MXFP4:   *block_size = 32u;  *type_size = 17u;  return 1;
        default:
            return 0;
    }
}

static gguf_status gguf_tensor_expected_size(const gguf_tensor_info_t *tensor, uint64_t *size, char *error, size_t error_size) {
    const char *name = "";
    uint64_t block_size = 0;
    uint64_t type_size = 0;
    uint64_t bytes = 0;
    uint32_t index = 0;

    if (tensor == NULL || size == NULL) {
        gguf_set_error(error, error_size, "Invalid tensor");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    name = tensor->name.string == NULL ? "" : tensor->name.string;

    if (!gguf_type_block_size(tensor->type, &block_size, &type_size) || block_size == 0 || type_size == 0) {
        gguf_set_error(error, error_size, "Tensor '%s' has unsupported type %s (%" PRIu32 ")",
                       name,
                       gguf_ggml_type_name(tensor->type),
                       tensor->type);
        return GGUF_STATUS_INVALID_FORMAT;
    }

    if (tensor->n_dimensions == 0 || tensor->dimensions == NULL) {
        gguf_set_error(error, error_size, "Tensor '%s' has no dimensions", name);
        return GGUF_STATUS_INVALID_FORMAT;
    }

    for (index = 0; index < tensor->n_dimensions; ++index) {
        if (tensor->dimensions[index] == 0) {
            gguf_set_error(error, error_size, "Tensor '%s' has zero dimension %" PRIu32, name, index);
            return GGUF_STATUS_INVALID_FORMAT;
        }
    }

    if ((tensor->dimensions[0] % block_size) != 0u) {
        gguf_set_error(error, error_size, "Tensor '%s' dimension 0 is not divisible by block size %" PRIu64 " for type %s",
                       name,
                       block_size,
                       gguf_ggml_type_name(tensor->type));
        return GGUF_STATUS_INVALID_FORMAT;
    }

    if (gguf_mul_overflow_u64(tensor->dimensions[0] / block_size, type_size, &bytes)) {
        gguf_set_error(error, error_size, "Tensor '%s' size overflow", name);
        return GGUF_STATUS_INVALID_FORMAT;
    }

    for (index = 1; index < tensor->n_dimensions; ++index) {
        if (gguf_mul_overflow_u64(bytes, tensor->dimensions[index], &bytes)) {
            gguf_set_error(error, error_size, "Tensor '%s' size overflow", name);
            return GGUF_STATUS_INVALID_FORMAT;
        }
    }

    *size = bytes;
    return GGUF_STATUS_OK;
}

static gguf_status gguf_validate_tensor_layout(const gguf_file_t *file, uint32_t alignment, gguf_sorted_tensor_t *sorted, char *error, size_t error_size) {
    uint64_t index = 0;

    if (file == NULL) {
        gguf_set_error(error, error_size, "Invalid GGUF file");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0; index < file->header.tensor_count; ++index) {
        const gguf_tensor_info_t *tensor = &file->tensor_infos[index];
        const char *name = tensor->name.string == NULL ? "" : tensor->name.string;
        uint64_t expected_size = 0;
        uint64_t end = 0;
        gguf_status status = gguf_tensor_expected_size(tensor, &expected_size, error, error_size);

        if (status != GGUF_STATUS_OK) {
            return status;
        }
        if (tensor->offset > file->tensor_data_size) {
            gguf_set_error(error, error_size, "Tensor '%s' offset exceeds tensor data size", name);
            return GGUF_STATUS_INVALID_FORMAT;
        }
        if (alignment != 0 && (tensor->offset % alignment) != 0u) {
            gguf_set_error(error, error_size, "Tensor '%s' offset is not aligned to %u bytes", name, alignment);
            return GGUF_STATUS_INVALID_FORMAT;
        }
        if (gguf_add_overflow_u64(tensor->offset, expected_size, &end) || end > file->tensor_data_size) {
            gguf_set_error(error, error_size, "Tensor '%s' data range exceeds tensor_data size", name);
            return GGUF_STATUS_INVALID_FORMAT;
        }

        if (sorted != NULL) {
            sorted[index].index = index;
            sorted[index].offset = tensor->offset;
            sorted[index].end = end;
        }
    }

    if (sorted != NULL && file->header.tensor_count > 1u) {
        qsort(sorted, (size_t)file->header.tensor_count, sizeof(gguf_sorted_tensor_t), gguf_compare_sorted_tensors);
        for (index = 1; index < file->header.tensor_count; ++index) {
            const gguf_tensor_info_t *previous = &file->tensor_infos[sorted[index - 1u].index];
            const gguf_tensor_info_t *current = &file->tensor_infos[sorted[index].index];
            const char *previous_name = previous->name.string == NULL ? "" : previous->name.string;
            const char *current_name = current->name.string == NULL ? "" : current->name.string;

            if (sorted[index - 1u].end > sorted[index].offset) {
                gguf_set_error(error, error_size, "Tensor '%s' overlaps tensor '%s'", previous_name, current_name);
                return GGUF_STATUS_INVALID_FORMAT;
            }
        }
    }

    return GGUF_STATUS_OK;
}

static gguf_status gguf_finalize_tensor_sections(gguf_file_t *file, char *error, size_t error_size) {
    gguf_sorted_tensor_t *sorted = NULL;
    uint64_t index = 0;
    gguf_status status = GGUF_STATUS_OK;

    if (file->header.tensor_count == 0) {
        return GGUF_STATUS_OK;
    }

    if (file->header.tensor_count > (uint64_t)((size_t)-1) / sizeof(gguf_sorted_tensor_t)) {
        gguf_set_error(error, error_size, "Too many tensors to finalize");
        return GGUF_STATUS_OUT_OF_MEMORY;
    }

    file->tensor_sections = (gguf_tensor_section_t *)gguf_calloc_items((size_t)file->header.tensor_count, sizeof(gguf_tensor_section_t));
    sorted = (gguf_sorted_tensor_t *)gguf_calloc_items((size_t)file->header.tensor_count, sizeof(gguf_sorted_tensor_t));
    if (file->tensor_sections == NULL || sorted == NULL) {
        free(file->tensor_sections);
        file->tensor_sections = NULL;
        free(sorted);
        gguf_set_error(error, error_size, "Out of memory allocating tensor sections");
        return GGUF_STATUS_OUT_OF_MEMORY;
    }

    status = gguf_validate_tensor_layout(file, file->alignment, sorted, error, error_size);
    if (status != GGUF_STATUS_OK) {
        free(file->tensor_sections);
        file->tensor_sections = NULL;
        free(sorted);
        return status;
    }

    for (index = 0; index < file->header.tensor_count; ++index) {
        uint64_t tensor_index = sorted[index].index;
        uint64_t start = sorted[index].offset;
        uint64_t end = sorted[index].end;

        file->tensor_infos[tensor_index].size = end - start;
        file->tensor_infos[tensor_index].file_offset = file->tensor_data_offset + start;
        file->tensor_infos[tensor_index].data = file->tensor_data == NULL ? NULL : file->tensor_data + start;

        file->tensor_sections[tensor_index].name = file->tensor_infos[tensor_index].name.string;
        file->tensor_sections[tensor_index].name_len = file->tensor_infos[tensor_index].name.len;
        file->tensor_sections[tensor_index].offset = start;
        file->tensor_sections[tensor_index].file_offset = file->tensor_infos[tensor_index].file_offset;
        file->tensor_sections[tensor_index].size = end - start;
        file->tensor_sections[tensor_index].data = file->tensor_data == NULL ? NULL : file->tensor_data + start;
    }

    free(sorted);
    return GGUF_STATUS_OK;
}

static void gguf_free_internal(gguf_file_t *file) {
    uint64_t index = 0;

    if (file == NULL) {
        return;
    }

    if (file->metadata_kv != NULL) {
        for (index = 0; index < file->header.metadata_kv_count; ++index) {
            gguf_free_metadata_kv(&file->metadata_kv[index]);
        }
    }
    free(file->metadata_kv);
    file->metadata_kv = NULL;

    if (file->tensor_infos != NULL) {
        for (index = 0; index < file->header.tensor_count; ++index) {
            gguf_free_tensor_info(&file->tensor_infos[index]);
        }
    }
    free(file->tensor_infos);
    file->tensor_infos = NULL;

    free(file->tensor_sections);
    file->tensor_sections = NULL;

    free(file->tensor_data);
    file->tensor_data = NULL;
    file->tensor_data_size = 0;
    free(file->tensor_data_source_path);
    file->tensor_data_source_path = NULL;
    file->tensor_data_source_offset = 0;
    file->tensor_data_source_size = 0;
    file->tensor_data_offset = 0;
    file->alignment = 0;
    memset(&file->header, 0, sizeof(file->header));
}

uint64_t gguf_align_offset(uint64_t offset, uint32_t alignment) {
    uint32_t effective_alignment = alignment == 0 ? GGUF_DEFAULT_ALIGNMENT : alignment;

    return offset + (effective_alignment - (offset % effective_alignment)) % effective_alignment;
}

const char *gguf_status_string(gguf_status status) {
    switch (status) {
        case GGUF_STATUS_OK: return "ok";
        case GGUF_STATUS_INVALID_ARGUMENT: return "invalid argument";
        case GGUF_STATUS_IO_ERROR: return "io error";
        case GGUF_STATUS_INVALID_MAGIC: return "invalid magic";
        case GGUF_STATUS_UNSUPPORTED_VERSION: return "unsupported version";
        case GGUF_STATUS_INVALID_FORMAT: return "invalid format";
        case GGUF_STATUS_OUT_OF_MEMORY: return "out of memory";
        case GGUF_STATUS_NOT_IMPLEMENTED: return "not implemented";
        default: return "unknown";
    }
}

const char *gguf_ggml_type_name(uint32_t type) {
    switch (type) {
        case GGML_TYPE_F32: return "F32";
        case GGML_TYPE_F16: return "F16";
        case GGML_TYPE_Q4_0: return "Q4_0";
        case GGML_TYPE_Q4_1: return "Q4_1";
        case GGML_TYPE_Q5_0: return "Q5_0";
        case GGML_TYPE_Q5_1: return "Q5_1";
        case GGML_TYPE_Q8_0: return "Q8_0";
        case GGML_TYPE_Q8_1: return "Q8_1";
        case GGML_TYPE_Q2_K: return "Q2_K";
        case GGML_TYPE_Q3_K: return "Q3_K";
        case GGML_TYPE_Q4_K: return "Q4_K";
        case GGML_TYPE_Q5_K: return "Q5_K";
        case GGML_TYPE_Q6_K: return "Q6_K";
        case GGML_TYPE_Q8_K: return "Q8_K";
        case GGML_TYPE_IQ2_XXS: return "IQ2_XXS";
        case GGML_TYPE_IQ2_XS: return "IQ2_XS";
        case GGML_TYPE_IQ3_XXS: return "IQ3_XXS";
        case GGML_TYPE_IQ1_S: return "IQ1_S";
        case GGML_TYPE_IQ4_NL: return "IQ4_NL";
        case GGML_TYPE_IQ3_S: return "IQ3_S";
        case GGML_TYPE_IQ2_S: return "IQ2_S";
        case GGML_TYPE_IQ4_XS: return "IQ4_XS";
        case GGML_TYPE_I8: return "I8";
        case GGML_TYPE_I16: return "I16";
        case GGML_TYPE_I32: return "I32";
        case GGML_TYPE_I64: return "I64";
        case GGML_TYPE_F64: return "F64";
        case GGML_TYPE_IQ1_M: return "IQ1_M";
        case GGML_TYPE_BF16: return "BF16";
        case GGML_TYPE_TQ1_0: return "TQ1_0";
        case GGML_TYPE_TQ2_0: return "TQ2_0";
        case GGML_TYPE_MXFP4: return "MXFP4";
        case GGML_TYPE_COUNT: return "COUNT";
        default: return "UNKNOWN";
    }
}

const char *gguf_metadata_type_name(uint32_t type) {
    switch (type) {
        case GGUF_METADATA_VALUE_TYPE_UINT8: return "UINT8";
        case GGUF_METADATA_VALUE_TYPE_INT8: return "INT8";
        case GGUF_METADATA_VALUE_TYPE_UINT16: return "UINT16";
        case GGUF_METADATA_VALUE_TYPE_INT16: return "INT16";
        case GGUF_METADATA_VALUE_TYPE_UINT32: return "UINT32";
        case GGUF_METADATA_VALUE_TYPE_INT32: return "INT32";
        case GGUF_METADATA_VALUE_TYPE_FLOAT32: return "FLOAT32";
        case GGUF_METADATA_VALUE_TYPE_BOOL: return "BOOL";
        case GGUF_METADATA_VALUE_TYPE_STRING: return "STRING";
        case GGUF_METADATA_VALUE_TYPE_ARRAY: return "ARRAY";
        case GGUF_METADATA_VALUE_TYPE_UINT64: return "UINT64";
        case GGUF_METADATA_VALUE_TYPE_INT64: return "INT64";
        case GGUF_METADATA_VALUE_TYPE_FLOAT64: return "FLOAT64";
        default: return "UNKNOWN";
    }
}

const gguf_metadata_kv_t *gguf_find_metadata(const gguf_file_t *file, const char *key) {
    return gguf_find_metadata_internal(file, key);
}

void gguf_free(gguf_file_t *file) {
    gguf_free_internal(file);
}

static int gguf_fseek64(FILE *file, int64_t offset, int origin) {
#ifdef _WIN32
    return _fseeki64(file, offset, origin);
#else
    return fseeko(file, offset, origin);
#endif
}

static int64_t gguf_ftell64(FILE *file) {
#ifdef _WIN32
    return _ftelli64(file);
#else
    return ftello(file);
#endif
}

#ifdef _WIN32
static int gguf_get_file_identity(const char *path, BY_HANDLE_FILE_INFORMATION *info) {
    HANDLE handle = INVALID_HANDLE_VALUE;
    int result = 0;

    if (path == NULL || info == NULL) {
        return 0;
    }

    handle = CreateFileA(path,
                         FILE_READ_ATTRIBUTES,
                         FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                         NULL,
                         OPEN_EXISTING,
                         FILE_ATTRIBUTE_NORMAL,
                         NULL);
    if (handle == INVALID_HANDLE_VALUE) {
        return 0;
    }

    result = GetFileInformationByHandle(handle, info) != 0;
    CloseHandle(handle);
    return result;
}

static int gguf_paths_refer_to_same_file(const char *left, const char *right) {
    BY_HANDLE_FILE_INFORMATION left_info;
    BY_HANDLE_FILE_INFORMATION right_info;

    memset(&left_info, 0, sizeof(left_info));
    memset(&right_info, 0, sizeof(right_info));

    if (!gguf_get_file_identity(left, &left_info) ||
        !gguf_get_file_identity(right, &right_info)) {
        return 0;
    }

    return left_info.dwVolumeSerialNumber == right_info.dwVolumeSerialNumber &&
           left_info.nFileIndexHigh == right_info.nFileIndexHigh &&
           left_info.nFileIndexLow == right_info.nFileIndexLow;
}
#else
static int gguf_paths_refer_to_same_file(const char *left, const char *right) {
    struct stat left_stat;
    struct stat right_stat;

    if (left == NULL || right == NULL) {
        return 0;
    }
    if (stat(left, &left_stat) != 0 || stat(right, &right_stat) != 0) {
        return 0;
    }

    return left_stat.st_dev == right_stat.st_dev &&
           left_stat.st_ino == right_stat.st_ino;
}
#endif

static gguf_status gguf_parse_bytes_ex(const uint8_t *data, uint64_t size, uint64_t full_size, int copy_tensor_data, gguf_file_t *out_file, char *error, size_t error_size) {
    gguf_reader_t reader;
    uint64_t index = 0;
    gguf_status status = GGUF_STATUS_OK;

    if (data == NULL || out_file == NULL) {
        gguf_set_error(error, error_size, "Invalid argument");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    memset(out_file, 0, sizeof(*out_file));

    reader.data = data;
    reader.size = size;
    reader.pos = 0;
    reader.error = error;
    reader.error_size = error_size;

    if (!gguf_reader_read_u32(&reader, &out_file->header.magic) ||
        !gguf_reader_read_u32(&reader, &out_file->header.version) ||
        !gguf_reader_read_u64(&reader, &out_file->header.tensor_count) ||
        !gguf_reader_read_u64(&reader, &out_file->header.metadata_kv_count)) {
        status = GGUF_STATUS_INVALID_FORMAT;
        goto cleanup;
    }

    if (out_file->header.magic != GGUF_MAGIC) {
        gguf_set_error(error, error_size, "Invalid magic 0x%08" PRIX32, out_file->header.magic);
        status = GGUF_STATUS_INVALID_MAGIC;
        goto cleanup;
    }

    if (out_file->header.version != GGUF_VERSION) {
        gguf_set_error(error, error_size, "Unsupported GGUF version %" PRIu32, out_file->header.version);
        status = GGUF_STATUS_UNSUPPORTED_VERSION;
        goto cleanup;
    }

    if (out_file->header.metadata_kv_count > 0) {
        if (out_file->header.metadata_kv_count > (uint64_t)((size_t)-1) / sizeof(gguf_metadata_kv_t)) {
            gguf_set_error(error, error_size, "Too many metadata entries to allocate");
            status = GGUF_STATUS_OUT_OF_MEMORY;
            goto cleanup;
        }
        out_file->metadata_kv = (gguf_metadata_kv_t *)gguf_calloc_items((size_t)out_file->header.metadata_kv_count, sizeof(gguf_metadata_kv_t));
        if (out_file->metadata_kv == NULL) {
            gguf_set_error(error, error_size, "Out of memory allocating metadata entries");
            status = GGUF_STATUS_OUT_OF_MEMORY;
            goto cleanup;
        }
    }

    for (index = 0; index < out_file->header.metadata_kv_count; ++index) {
        if (!gguf_reader_read_metadata_kv(&reader, &out_file->metadata_kv[index])) {
            status = GGUF_STATUS_INVALID_FORMAT;
            goto cleanup;
        }
    }

    out_file->alignment = gguf_detect_alignment(out_file);
    if ((out_file->alignment % 8u) != 0u) {
        gguf_set_error(error, error_size, "Invalid general.alignment value %u", out_file->alignment);
        status = GGUF_STATUS_INVALID_FORMAT;
        goto cleanup;
    }

    if (out_file->header.tensor_count > 0) {
        if (out_file->header.tensor_count > (uint64_t)((size_t)-1) / sizeof(gguf_tensor_info_t)) {
            gguf_set_error(error, error_size, "Too many tensor infos to allocate");
            status = GGUF_STATUS_OUT_OF_MEMORY;
            goto cleanup;
        }
        out_file->tensor_infos = (gguf_tensor_info_t *)gguf_calloc_items((size_t)out_file->header.tensor_count, sizeof(gguf_tensor_info_t));
        if (out_file->tensor_infos == NULL) {
            gguf_set_error(error, error_size, "Out of memory allocating tensor infos");
            status = GGUF_STATUS_OUT_OF_MEMORY;
            goto cleanup;
        }
    }

    for (index = 0; index < out_file->header.tensor_count; ++index) {
        if (!gguf_reader_read_tensor_info(&reader, &out_file->tensor_infos[index])) {
            status = GGUF_STATUS_INVALID_FORMAT;
            goto cleanup;
        }
    }

    out_file->tensor_data_offset = gguf_align_offset(reader.pos, out_file->alignment);
    if (out_file->tensor_data_offset > full_size) {
        gguf_set_error(error, error_size, "Tensor data offset exceeds file size");
        status = GGUF_STATUS_INVALID_FORMAT;
        goto cleanup;
    }

    out_file->tensor_data_size = full_size - out_file->tensor_data_offset;
    if (copy_tensor_data && out_file->tensor_data_size > 0) {
        if (out_file->tensor_data_offset > reader.size ||
            out_file->tensor_data_size > reader.size - out_file->tensor_data_offset) {
            gguf_set_error(error, error_size, "Unexpected end of file at byte %" PRIu64, reader.size);
            status = GGUF_STATUS_INVALID_FORMAT;
            goto cleanup;
        }
        if (out_file->tensor_data_size > (uint64_t)((size_t)-1)) {
            gguf_set_error(error, error_size, "Tensor data is too large to allocate");
            status = GGUF_STATUS_OUT_OF_MEMORY;
            goto cleanup;
        }
        out_file->tensor_data = (uint8_t *)malloc((size_t)out_file->tensor_data_size);
        if (out_file->tensor_data == NULL) {
            gguf_set_error(error, error_size, "Out of memory allocating tensor data");
            status = GGUF_STATUS_OUT_OF_MEMORY;
            goto cleanup;
        }
        memcpy(out_file->tensor_data, data + out_file->tensor_data_offset, (size_t)out_file->tensor_data_size);
    }

    status = gguf_finalize_tensor_sections(out_file, error, error_size);

cleanup:
    if (status != GGUF_STATUS_OK) {
        gguf_free_internal(out_file);
    }
    return status;
}

static gguf_status gguf_parse_bytes(const uint8_t *data, uint64_t size, gguf_file_t *out_file, char *error, size_t error_size) {
    return gguf_parse_bytes_ex(data, size, size, 1, out_file, error, error_size);
}

gguf_status gguf_load_file(const char *path, gguf_file_t *out_file, char *error, size_t error_size) {
    FILE *file = NULL;
    int64_t file_size = 0;
    uint8_t *file_bytes = NULL;
    gguf_status status = GGUF_STATUS_OK;
    uint64_t capacity = 0;
    uint64_t bytes_read = 0;
    char parse_error[512];

    if (path == NULL || out_file == NULL) {
        gguf_set_error(error, error_size, "Invalid argument");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    file = fopen(path, "rb");
    if (file == NULL) {
        gguf_set_error(error, error_size, "Unable to open file '%s': %s", path, strerror(errno));
        return GGUF_STATUS_IO_ERROR;
    }

    if (gguf_fseek64(file, 0, SEEK_END) != 0) {
        gguf_set_error(error, error_size, "Unable to seek in file '%s'", path);
        fclose(file);
        return GGUF_STATUS_IO_ERROR;
    }

    file_size = gguf_ftell64(file);
    if (file_size < 0) {
        gguf_set_error(error, error_size, "Unable to determine file size for '%s'", path);
        fclose(file);
        return GGUF_STATUS_IO_ERROR;
    }

    if (gguf_fseek64(file, 0, SEEK_SET) != 0) {
        gguf_set_error(error, error_size, "Unable to rewind file '%s'", path);
        fclose(file);
        return GGUF_STATUS_IO_ERROR;
    }

    if (file_size == 0) {
        fclose(file);
        return gguf_parse_bytes(NULL, 0, out_file, error, error_size);
    }

    capacity = (uint64_t)file_size < 65536u ? (uint64_t)file_size : 65536u;
    if (capacity > (uint64_t)((size_t)-1)) {
        gguf_set_error(error, error_size, "File '%s' is too large to allocate header buffer", path);
        fclose(file);
        return GGUF_STATUS_OUT_OF_MEMORY;
    }

    file_bytes = (uint8_t *)malloc((size_t)capacity);
    if (file_bytes == NULL) {
        gguf_set_error(error, error_size, "Out of memory reading file '%s'", path);
        fclose(file);
        return GGUF_STATUS_OUT_OF_MEMORY;
    }

    while (1) {
        memset(parse_error, 0, sizeof(parse_error));

        if (bytes_read < capacity) {
            size_t to_read = (size_t)(capacity - bytes_read);
            if (fread(file_bytes + bytes_read, 1, to_read, file) != to_read) {
                gguf_set_error(error, error_size, "Unable to read file '%s'", path);
                free(file_bytes);
                fclose(file);
                return GGUF_STATUS_IO_ERROR;
            }
            bytes_read = capacity;
        }

        status = gguf_parse_bytes_ex(file_bytes, bytes_read, (uint64_t)file_size, 0, out_file, parse_error, sizeof(parse_error));
        if (status == GGUF_STATUS_OK) {
            out_file->tensor_data_source_path = gguf_strdup_string(path);
            if (out_file->tensor_data_source_path == NULL && out_file->tensor_data_size != 0) {
                gguf_set_error(parse_error, sizeof(parse_error), "Out of memory storing tensor data source path");
                gguf_free_internal(out_file);
                status = GGUF_STATUS_OUT_OF_MEMORY;
            }
            else {
                out_file->tensor_data_source_offset = out_file->tensor_data_offset;
                out_file->tensor_data_source_size = out_file->tensor_data_size;
            }
            break;
        }

        if (strncmp(parse_error, "Unexpected end of file", 22u) != 0 ||
            capacity >= (uint64_t)file_size) {
            break;
        }

        capacity *= 2u;
        if (capacity > (uint64_t)file_size) {
            capacity = (uint64_t)file_size;
        }
        if (capacity > (uint64_t)((size_t)-1)) {
            gguf_set_error(error, error_size, "File '%s' header is too large to allocate", path);
            status = GGUF_STATUS_OUT_OF_MEMORY;
            break;
        }

        {
            uint8_t *new_file_bytes = (uint8_t *)realloc(file_bytes, (size_t)capacity);
            if (new_file_bytes == NULL) {
                gguf_set_error(error, error_size, "Out of memory growing header buffer for '%s'", path);
                status = GGUF_STATUS_OUT_OF_MEMORY;
                break;
            }
            file_bytes = new_file_bytes;
        }
    }

    if (status != GGUF_STATUS_OK && parse_error[0] != '\0') {
        gguf_set_error(error, error_size, "%s", parse_error);
    }

    free(file_bytes);
    fclose(file);
    return status;
}

gguf_status gguf_load_memory(const void *data, uint64_t size, gguf_file_t *out_file, char *error, size_t error_size) {
    if (data == NULL || out_file == NULL) {
        gguf_set_error(error, error_size, "Invalid argument");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    return gguf_parse_bytes((const uint8_t *)data, size, out_file, error, error_size);
}

static int gguf_writer_write_string(gguf_writer_t *writer, const gguf_string_t *string) {
    if (string == NULL || (string->len != 0 && string->string == NULL)) {
        gguf_set_error(writer->error, writer->error_size, "Invalid GGUF string");
        return 0;
    }

    if (!gguf_writer_write_u64(writer, string->len)) {
        return 0;
    }

    return gguf_writer_write_bytes(writer, string->string, (size_t)string->len);
}

static int gguf_writer_write_metadata_value(gguf_writer_t *writer, uint32_t type, const gguf_metadata_value_t *value) {
    uint64_t index = 0;

    if (value == NULL || value->type != type) {
        gguf_set_error(writer->error, writer->error_size, "Metadata value type mismatch");
        return 0;
    }

    switch (type) {
        case GGUF_METADATA_VALUE_TYPE_UINT8:
            return gguf_writer_write_u8(writer, value->value.uint8);
        case GGUF_METADATA_VALUE_TYPE_INT8:
            return gguf_writer_write_u8(writer, (uint8_t)value->value.int8);
        case GGUF_METADATA_VALUE_TYPE_UINT16:
            return gguf_writer_write_u16(writer, value->value.uint16);
        case GGUF_METADATA_VALUE_TYPE_INT16:
            return gguf_writer_write_i16(writer, value->value.int16);
        case GGUF_METADATA_VALUE_TYPE_UINT32:
            return gguf_writer_write_u32(writer, value->value.uint32);
        case GGUF_METADATA_VALUE_TYPE_INT32:
            return gguf_writer_write_i32(writer, value->value.int32);
        case GGUF_METADATA_VALUE_TYPE_FLOAT32:
            return gguf_writer_write_f32(writer, value->value.float32);
        case GGUF_METADATA_VALUE_TYPE_BOOL:
            return gguf_writer_write_u8(writer, value->value.bool_ ? 1u : 0u);
        case GGUF_METADATA_VALUE_TYPE_STRING:
            return gguf_writer_write_string(writer, &value->value.string);
        case GGUF_METADATA_VALUE_TYPE_ARRAY:
            if (!gguf_writer_write_u32(writer, value->value.array.type) ||
                !gguf_writer_write_u64(writer, value->value.array.len)) {
                return 0;
            }
            for (index = 0; index < value->value.array.len; ++index) {
                if (!gguf_writer_write_metadata_value(writer, value->value.array.type, &value->value.array.items[index])) {
                    return 0;
                }
            }
            return 1;
        case GGUF_METADATA_VALUE_TYPE_UINT64:
            return gguf_writer_write_u64(writer, value->value.uint64);
        case GGUF_METADATA_VALUE_TYPE_INT64:
            return gguf_writer_write_i64(writer, value->value.int64);
        case GGUF_METADATA_VALUE_TYPE_FLOAT64:
            return gguf_writer_write_f64(writer, value->value.float64);
        default:
            gguf_set_error(writer->error, writer->error_size, "Unsupported metadata value type %u", type);
            return 0;
    }
}

static int gguf_writer_write_metadata_kv(gguf_writer_t *writer, const gguf_metadata_kv_t *kv) {
    if (kv == NULL) {
        gguf_set_error(writer->error, writer->error_size, "Invalid metadata entry");
        return 0;
    }

    if (!gguf_writer_write_string(writer, &kv->key) ||
        !gguf_writer_write_u32(writer, kv->value_type) ||
        !gguf_writer_write_metadata_value(writer, kv->value_type, &kv->value)) {
        return 0;
    }

    return 1;
}

static int gguf_writer_write_tensor_info(gguf_writer_t *writer, const gguf_tensor_info_t *tensor) {
    uint32_t index = 0;

    if (tensor == NULL) {
        gguf_set_error(writer->error, writer->error_size, "Invalid tensor info");
        return 0;
    }

    if (!gguf_writer_write_string(writer, &tensor->name) ||
        !gguf_writer_write_u32(writer, tensor->n_dimensions)) {
        return 0;
    }

    for (index = 0; index < tensor->n_dimensions; ++index) {
        if (!gguf_writer_write_u64(writer, tensor->dimensions[index])) {
            return 0;
        }
    }

    return gguf_writer_write_u32(writer, tensor->type) &&
           gguf_writer_write_u64(writer, tensor->offset);
}

static gguf_status gguf_validate_for_write(const gguf_file_t *file, uint32_t *alignment_out, char *error, size_t error_size) {
    uint32_t alignment = 0;
    uint64_t index = 0;
    gguf_status status = GGUF_STATUS_OK;
    gguf_sorted_tensor_t *sorted = NULL;

    if (file == NULL || alignment_out == NULL) {
        gguf_set_error(error, error_size, "Invalid argument");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    if (file->header.magic != 0 && file->header.magic != GGUF_MAGIC) {
        gguf_set_error(error, error_size, "Invalid magic 0x%08" PRIX32, file->header.magic);
        return GGUF_STATUS_INVALID_MAGIC;
    }

    if (file->header.version != 0 && file->header.version != GGUF_VERSION) {
        gguf_set_error(error, error_size, "Unsupported GGUF version %" PRIu32, file->header.version);
        return GGUF_STATUS_UNSUPPORTED_VERSION;
    }

    if (file->header.metadata_kv_count > 0 && file->metadata_kv == NULL) {
        gguf_set_error(error, error_size, "Metadata entries are missing");
        return GGUF_STATUS_INVALID_FORMAT;
    }

    if (file->header.tensor_count > 0 && file->tensor_infos == NULL) {
        gguf_set_error(error, error_size, "Tensor infos are missing");
        return GGUF_STATUS_INVALID_FORMAT;
    }

    if (file->tensor_data_size > 0 && file->tensor_data == NULL && file->tensor_data_source_path == NULL) {
        gguf_set_error(error, error_size, "Tensor data is missing");
        return GGUF_STATUS_INVALID_FORMAT;
    }
    if (file->tensor_data_source_path != NULL && file->tensor_data_source_size < file->tensor_data_size) {
        gguf_set_error(error, error_size, "Tensor data source is smaller than tensor data");
        return GGUF_STATUS_INVALID_FORMAT;
    }

    alignment = file->alignment == 0 ? gguf_detect_alignment(file) : file->alignment;
    if (alignment == 0) {
        alignment = GGUF_DEFAULT_ALIGNMENT;
    }
    if ((alignment % 8u) != 0u) {
        gguf_set_error(error, error_size, "Invalid general.alignment value %u", alignment);
        return GGUF_STATUS_INVALID_FORMAT;
    }

    for (index = 0; index < file->header.metadata_kv_count; ++index) {
        const gguf_metadata_kv_t *kv = &file->metadata_kv[index];
        if (kv->key.len != 0 && kv->key.string == NULL) {
            gguf_set_error(error, error_size, "Metadata key %" PRIu64 " is missing", index);
            return GGUF_STATUS_INVALID_FORMAT;
        }
        if (kv->value.type != kv->value_type) {
            gguf_set_error(error, error_size, "Metadata value type mismatch for key '%s'", kv->key.string == NULL ? "" : kv->key.string);
            return GGUF_STATUS_INVALID_FORMAT;
        }
    }

    for (index = 0; index < file->header.tensor_count; ++index) {
        const gguf_tensor_info_t *tensor = &file->tensor_infos[index];
        if (tensor->name.len != 0 && tensor->name.string == NULL) {
            gguf_set_error(error, error_size, "Tensor name %" PRIu64 " is missing", index);
            return GGUF_STATUS_INVALID_FORMAT;
        }
        if (tensor->n_dimensions != 0 && tensor->dimensions == NULL) {
            gguf_set_error(error, error_size, "Tensor '%s' has no dimension buffer", tensor->name.string == NULL ? "" : tensor->name.string);
            return GGUF_STATUS_INVALID_FORMAT;
        }
    }

    if (file->header.tensor_count > 0) {
        if (file->header.tensor_count > (uint64_t)((size_t)-1) / sizeof(gguf_sorted_tensor_t)) {
            gguf_set_error(error, error_size, "Too many tensors to validate");
            return GGUF_STATUS_OUT_OF_MEMORY;
        }

        sorted = (gguf_sorted_tensor_t *)gguf_calloc_items((size_t)file->header.tensor_count, sizeof(gguf_sorted_tensor_t));
        if (sorted == NULL) {
            gguf_set_error(error, error_size, "Out of memory validating tensor layout");
            return GGUF_STATUS_OUT_OF_MEMORY;
        }

        status = gguf_validate_tensor_layout(file, alignment, sorted, error, error_size);
        free(sorted);
        if (status != GGUF_STATUS_OK) {
            return status;
        }
    }

    *alignment_out = alignment;
    return GGUF_STATUS_OK;
}

static int gguf_writer_write_u64_count(gguf_writer_t *writer, uint64_t bytes) {
    if (writer->pos > UINT64_MAX - bytes) {
        gguf_set_error(writer->error, writer->error_size, "Serialized GGUF size overflow");
        return 0;
    }

    writer->pos += bytes;
    return 1;
}

static int gguf_writer_write_data_chunks(gguf_writer_t *writer, const uint8_t *data, uint64_t size) {
    uint64_t written = 0;

    if (size == 0) {
        return 1;
    }
    if (data == NULL) {
        gguf_set_error(writer->error, writer->error_size, "Tensor data is missing");
        return 0;
    }
    if (writer->mode == GGUF_WRITER_MODE_COUNT) {
        return gguf_writer_write_u64_count(writer, size);
    }

    while (written < size) {
        uint64_t remaining = size - written;
        size_t chunk = remaining > 65536u ? 65536u : (size_t)remaining;
        if (!gguf_writer_write_bytes(writer, data + written, chunk)) {
            return 0;
        }
        written += (uint64_t)chunk;
    }

    return 1;
}

static int gguf_writer_write_source_chunks(gguf_writer_t *writer, const char *path, uint64_t offset, uint64_t size) {
    FILE *input = NULL;
    uint8_t *buffer = NULL;
    uint64_t remaining = size;

    if (size == 0) {
        return 1;
    }
    if (path == NULL) {
        gguf_set_error(writer->error, writer->error_size, "Tensor data source path is missing");
        return 0;
    }
    if (writer->mode == GGUF_WRITER_MODE_COUNT) {
        return gguf_writer_write_u64_count(writer, size);
    }
    if (offset > (uint64_t)INT64_MAX) {
        gguf_set_error(writer->error, writer->error_size, "Tensor data source offset is too large");
        return 0;
    }

    input = fopen(path, "rb");
    if (input == NULL) {
        gguf_set_error(writer->error, writer->error_size, "Unable to open tensor data source '%s': %s", path, strerror(errno));
        return 0;
    }

    if (gguf_fseek64(input, (int64_t)offset, SEEK_SET) != 0) {
        gguf_set_error(writer->error, writer->error_size, "Unable to seek tensor data source '%s'", path);
        fclose(input);
        return 0;
    }

    buffer = (uint8_t *)malloc(65536u);
    if (buffer == NULL) {
        gguf_set_error(writer->error, writer->error_size, "Out of memory allocating tensor data stream buffer");
        fclose(input);
        return 0;
    }

    while (remaining != 0) {
        size_t chunk = remaining > 65536u ? 65536u : (size_t)remaining;
        if (fread(buffer, 1, chunk, input) != chunk) {
            gguf_set_error(writer->error, writer->error_size, "Unable to read tensor data source '%s'", path);
            free(buffer);
            fclose(input);
            return 0;
        }
        if (!gguf_writer_write_bytes(writer, buffer, chunk)) {
            free(buffer);
            fclose(input);
            return 0;
        }
        remaining -= (uint64_t)chunk;
    }

    free(buffer);
    fclose(input);
    return 1;
}

static int gguf_writer_write_tensor_data(gguf_writer_t *writer, const gguf_file_t *file) {
    if (file->tensor_data != NULL) {
        return gguf_writer_write_data_chunks(writer, file->tensor_data, file->tensor_data_size);
    }

    return gguf_writer_write_source_chunks(writer,
                                           file->tensor_data_source_path,
                                           file->tensor_data_source_offset,
                                           file->tensor_data_size);
}

static gguf_status gguf_serialize_writer(gguf_writer_t *writer, const gguf_file_t *file, uint32_t alignment, char *error, size_t error_size) {
    gguf_status status = GGUF_STATUS_OK;
    uint32_t magic = file->header.magic == 0 ? GGUF_MAGIC : file->header.magic;
    uint32_t version = file->header.version == 0 ? GGUF_VERSION : file->header.version;
    uint64_t index = 0;
    uint64_t aligned_pos = 0;
    static const uint8_t zero_padding[64] = {0};

    if (writer == NULL || file == NULL) {
        gguf_set_error(error, error_size, "Invalid argument");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    if (!gguf_writer_write_u32(writer, magic) ||
        !gguf_writer_write_u32(writer, version) ||
        !gguf_writer_write_u64(writer, file->header.tensor_count) ||
        !gguf_writer_write_u64(writer, file->header.metadata_kv_count)) {
        status = GGUF_STATUS_IO_ERROR;
        return status;
    }

    for (index = 0; index < file->header.metadata_kv_count; ++index) {
        if (!gguf_writer_write_metadata_kv(writer, &file->metadata_kv[index])) {
            status = GGUF_STATUS_IO_ERROR;
            return status;
        }
    }

    for (index = 0; index < file->header.tensor_count; ++index) {
        if (!gguf_writer_write_tensor_info(writer, &file->tensor_infos[index])) {
            status = GGUF_STATUS_IO_ERROR;
            return status;
        }
    }

    aligned_pos = gguf_align_offset(writer->pos, alignment);
    while (writer->pos < aligned_pos) {
        size_t chunk = (size_t)((aligned_pos - writer->pos) > (uint64_t)sizeof(zero_padding) ? sizeof(zero_padding) : (aligned_pos - writer->pos));
        if (!gguf_writer_write_bytes(writer, zero_padding, chunk)) {
            status = GGUF_STATUS_IO_ERROR;
            return status;
        }
    }

    if (!gguf_writer_write_tensor_data(writer, file)) {
        status = GGUF_STATUS_IO_ERROR;
        return status;
    }

    return status;
}

gguf_status gguf_save_file(const char *path, const gguf_file_t *file, char *error, size_t error_size) {
    FILE *output = NULL;
    gguf_writer_t writer;
    gguf_status status = GGUF_STATUS_OK;
    uint32_t alignment = 0;

    if (path == NULL || file == NULL) {
        gguf_set_error(error, error_size, "Invalid argument");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    status = gguf_validate_for_write(file, &alignment, error, error_size);
    if (status != GGUF_STATUS_OK) {
        return status;
    }

    if (file->tensor_data == NULL &&
        file->tensor_data_source_path != NULL &&
        gguf_paths_refer_to_same_file(path, file->tensor_data_source_path)) {
        gguf_set_error(error, error_size, "Refusing to overwrite tensor data source '%s' while streaming from it", path);
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    output = fopen(path, "wb");
    if (output == NULL) {
        gguf_set_error(error, error_size, "Unable to create file '%s': %s", path, strerror(errno));
        return GGUF_STATUS_IO_ERROR;
    }

    memset(&writer, 0, sizeof(writer));
    writer.file = output;
    writer.mode = GGUF_WRITER_MODE_FILE;
    writer.error = error;
    writer.error_size = error_size;

    status = gguf_serialize_writer(&writer, file, alignment, error, error_size);

    if (output != NULL) {
        if (fclose(output) != 0 && status == GGUF_STATUS_OK) {
            gguf_set_error(error, error_size, "Unable to finalize output file '%s'", path);
            status = GGUF_STATUS_IO_ERROR;
        }
    }
    return status;
}

gguf_status gguf_serialized_size(const gguf_file_t *file, uint64_t *size, char *error, size_t error_size) {
    gguf_writer_t writer;
    gguf_status status = GGUF_STATUS_OK;
    uint32_t alignment = 0;

    if (file == NULL || size == NULL) {
        gguf_set_error(error, error_size, "Invalid argument");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    *size = 0;

    status = gguf_validate_for_write(file, &alignment, error, error_size);
    if (status != GGUF_STATUS_OK) {
        return status;
    }

    memset(&writer, 0, sizeof(writer));
    writer.mode = GGUF_WRITER_MODE_COUNT;
    writer.error = error;
    writer.error_size = error_size;

    status = gguf_serialize_writer(&writer, file, alignment, error, error_size);
    if (status != GGUF_STATUS_OK) {
        return status;
    }

    *size = writer.pos;
    return GGUF_STATUS_OK;
}

gguf_status gguf_serialize_to_memory(const gguf_file_t *file, uint8_t **data, uint64_t *size, char *error, size_t error_size) {
    gguf_writer_t writer;
    gguf_status status = GGUF_STATUS_OK;
    uint32_t alignment = 0;
    uint8_t *buffer = NULL;
    uint64_t serialized_size = 0;

    if (file == NULL || data == NULL || size == NULL) {
        gguf_set_error(error, error_size, "Invalid argument");
        return GGUF_STATUS_INVALID_ARGUMENT;
    }

    *data = NULL;
    *size = 0;

    status = gguf_validate_for_write(file, &alignment, error, error_size);
    if (status != GGUF_STATUS_OK) {
        return status;
    }

    memset(&writer, 0, sizeof(writer));
    writer.mode = GGUF_WRITER_MODE_COUNT;
    writer.error = error;
    writer.error_size = error_size;

    status = gguf_serialize_writer(&writer, file, alignment, error, error_size);
    if (status != GGUF_STATUS_OK) {
        return status;
    }

    if (writer.pos > (uint64_t)((size_t)-1)) {
        gguf_set_error(error, error_size, "Serialized GGUF is too large to allocate");
        return GGUF_STATUS_OUT_OF_MEMORY;
    }

    buffer = (uint8_t *)malloc((size_t)writer.pos);
    if (writer.pos != 0 && buffer == NULL) {
        gguf_set_error(error, error_size, "Out of memory allocating serialized GGUF");
        return GGUF_STATUS_OUT_OF_MEMORY;
    }

    serialized_size = writer.pos;

    memset(&writer, 0, sizeof(writer));
    writer.buffer = buffer;
    writer.mode = GGUF_WRITER_MODE_BUFFER;
    writer.error = error;
    writer.error_size = error_size;
    writer.pos = 0;
    writer.capacity = serialized_size;

    status = gguf_serialize_writer(&writer, file, alignment, error, error_size);
    if (status != GGUF_STATUS_OK) {
        free(buffer);
        return status;
    }

    *data = buffer;
    *size = writer.pos;
    return GGUF_STATUS_OK;
}

void gguf_print_summary(const gguf_file_t *file, FILE *stream) {
    const gguf_metadata_kv_t *architecture = NULL;
    const gguf_metadata_kv_t *quantization_version = NULL;
    uint64_t index = 0;
    uint64_t preview_count = 0;

    if (file == NULL || stream == NULL) {
        return;
    }

    architecture = gguf_find_metadata(file, "general.architecture");
    quantization_version = gguf_find_metadata(file, "general.quantization_version");

    fprintf(stream, "format: %s\n", GGUF_FORMAT_NAME);
    fprintf(stream, "magic: 0x%08" PRIX32 "\n", file->header.magic);
    fprintf(stream, "version: %" PRIu32 "\n", file->header.version);
    fprintf(stream, "metadata_kv_count: %" PRIu64 "\n", file->header.metadata_kv_count);
    fprintf(stream, "tensor_count: %" PRIu64 "\n", file->header.tensor_count);
    fprintf(stream, "alignment: %" PRIu32 "\n", file->alignment == 0 ? GGUF_DEFAULT_ALIGNMENT : file->alignment);
    fprintf(stream, "tensor_data_offset: %" PRIu64 "\n", file->tensor_data_offset);
    fprintf(stream, "tensor_data_size: %" PRIu64 "\n", file->tensor_data_size);

    if (architecture != NULL && architecture->value_type == GGUF_METADATA_VALUE_TYPE_STRING) {
        fprintf(stream, "architecture: %s\n", architecture->value.value.string.string);
    }

    if (quantization_version != NULL) {
        switch (quantization_version->value_type) {
            case GGUF_METADATA_VALUE_TYPE_UINT32:
                fprintf(stream, "quantization_version: %" PRIu32 "\n", quantization_version->value.value.uint32);
                break;
            case GGUF_METADATA_VALUE_TYPE_UINT64:
                fprintf(stream, "quantization_version: %" PRIu64 "\n", quantization_version->value.value.uint64);
                break;
            case GGUF_METADATA_VALUE_TYPE_INT32:
                fprintf(stream, "quantization_version: %" PRId32 "\n", quantization_version->value.value.int32);
                break;
            case GGUF_METADATA_VALUE_TYPE_INT64:
                fprintf(stream, "quantization_version: %" PRId64 "\n", quantization_version->value.value.int64);
                break;
            default:
                break;
        }
    }

    preview_count = file->header.tensor_count < 10u ? file->header.tensor_count : 10u;
    fprintf(stream, "tensor_sections_preview: %" PRIu64 "\n", preview_count);
    for (index = 0; index < preview_count; ++index) {
        const gguf_tensor_info_t *tensor = &file->tensor_infos[index];
        fprintf(stream,
                "  [%02" PRIu64 "] %s type=%s offset=%" PRIu64 " size=%" PRIu64 " file_offset=%" PRIu64 "\n",
                index,
                tensor->name.string == NULL ? "" : tensor->name.string,
                gguf_ggml_type_name(tensor->type),
                tensor->offset,
                tensor->size,
                tensor->file_offset);
    }
}
