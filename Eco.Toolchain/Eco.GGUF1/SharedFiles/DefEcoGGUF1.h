#ifndef __DEF_ECO_GGUF_1_H__
#define __DEF_ECO_GGUF_1_H__

#include "IEcoBase1.h"

#define ECO_GGUF1_MAGIC                0x46554747u
#define ECO_GGUF1_VERSION_3            3u
#define ECO_GGUF1_DEFAULT_ALIGNMENT    32u
#define ECO_GGUF1_MAX_TENSOR_NAME      64u
#define ECO_GGUF1_MAX_DIMS             4u

/* Well-known metadata keys */
#define ECO_GGUF1_KEY_GENERAL_ARCHITECTURE           "general.architecture"
#define ECO_GGUF1_KEY_GENERAL_ALIGNMENT              "general.alignment"
#define ECO_GGUF1_KEY_GENERAL_QUANTIZATION_VERSION   "general.quantization_version"
#define ECO_GGUF1_KEY_GENERAL_FILE_TYPE              "general.file_type"

/* ggml_type values from gguf.md */
#define ECO_GGUF1_TENSOR_TYPE_F32        0u
#define ECO_GGUF1_TENSOR_TYPE_F16        1u
#define ECO_GGUF1_TENSOR_TYPE_Q4_0       2u
#define ECO_GGUF1_TENSOR_TYPE_Q4_1       3u
#define ECO_GGUF1_TENSOR_TYPE_Q5_0       6u
#define ECO_GGUF1_TENSOR_TYPE_Q5_1       7u
#define ECO_GGUF1_TENSOR_TYPE_Q8_0       8u
#define ECO_GGUF1_TENSOR_TYPE_Q8_1       9u
#define ECO_GGUF1_TENSOR_TYPE_Q2_K       10u
#define ECO_GGUF1_TENSOR_TYPE_Q3_K       11u
#define ECO_GGUF1_TENSOR_TYPE_Q4_K       12u
#define ECO_GGUF1_TENSOR_TYPE_Q5_K       13u
#define ECO_GGUF1_TENSOR_TYPE_Q6_K       14u
#define ECO_GGUF1_TENSOR_TYPE_Q8_K       15u
#define ECO_GGUF1_TENSOR_TYPE_IQ2_XXS    16u
#define ECO_GGUF1_TENSOR_TYPE_IQ2_XS     17u
#define ECO_GGUF1_TENSOR_TYPE_IQ3_XXS    18u
#define ECO_GGUF1_TENSOR_TYPE_IQ1_S      19u
#define ECO_GGUF1_TENSOR_TYPE_IQ4_NL     20u
#define ECO_GGUF1_TENSOR_TYPE_IQ3_S      21u
#define ECO_GGUF1_TENSOR_TYPE_IQ2_S      22u
#define ECO_GGUF1_TENSOR_TYPE_IQ4_XS     23u
#define ECO_GGUF1_TENSOR_TYPE_I8         24u
#define ECO_GGUF1_TENSOR_TYPE_I16        25u
#define ECO_GGUF1_TENSOR_TYPE_I32        26u
#define ECO_GGUF1_TENSOR_TYPE_I64        27u
#define ECO_GGUF1_TENSOR_TYPE_F64        28u
#define ECO_GGUF1_TENSOR_TYPE_IQ1_M      29u
#define ECO_GGUF1_TENSOR_TYPE_BF16       30u
#define ECO_GGUF1_TENSOR_TYPE_TQ1_0      34u
#define ECO_GGUF1_TENSOR_TYPE_TQ2_0      35u
#define ECO_GGUF1_TENSOR_TYPE_MXFP4      39u
#define ECO_GGUF1_TENSOR_TYPE_COUNT      40u

/* gguf metadata value types from gguf.md */
#define ECO_GGUF1_METADATA_VALUE_TYPE_UINT8      0u
#define ECO_GGUF1_METADATA_VALUE_TYPE_INT8       1u
#define ECO_GGUF1_METADATA_VALUE_TYPE_UINT16     2u
#define ECO_GGUF1_METADATA_VALUE_TYPE_INT16      3u
#define ECO_GGUF1_METADATA_VALUE_TYPE_UINT32     4u
#define ECO_GGUF1_METADATA_VALUE_TYPE_INT32      5u
#define ECO_GGUF1_METADATA_VALUE_TYPE_FLOAT32    6u
#define ECO_GGUF1_METADATA_VALUE_TYPE_BOOL       7u
#define ECO_GGUF1_METADATA_VALUE_TYPE_STRING     8u
#define ECO_GGUF1_METADATA_VALUE_TYPE_ARRAY      9u
#define ECO_GGUF1_METADATA_VALUE_TYPE_UINT64     10u
#define ECO_GGUF1_METADATA_VALUE_TYPE_INT64      11u
#define ECO_GGUF1_METADATA_VALUE_TYPE_FLOAT64    12u

/* Common file_type values */
#define ECO_GGUF1_FILE_TYPE_ALL_F32              0u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_F16           1u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q4_0          2u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q4_1          3u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q4_1_SOME_F16 4u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q8_0          7u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q5_0          8u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q5_1          9u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q2_K          10u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q3_K_S        11u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q3_K_M        12u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q3_K_L        13u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q4_K_S        14u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q4_K_M        15u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q5_K_S        16u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q5_K_M        17u
#define ECO_GGUF1_FILE_TYPE_MOSTLY_Q6_K          18u

#endif /* __DEF_ECO_GGUF_1_H__ */
