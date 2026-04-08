import unittest

from agent.header_parser import build_method_map, parse_vtbl_methods
from agent.verifier import verify_ecomain


MATH_HEADER = """
typedef struct IEcoMathC89VTbl {
    int16_t (ECOCALLMETHOD *QueryInterface)(void);
    uint32_t (ECOCALLMETHOD *AddRef)(void);
    uint32_t (ECOCALLMETHOD *Release)(void);
    double (ECOCALLMETHOD *pow)(IEcoMathC89Ptr_t me, double x, double y);
    double (ECOCALLMETHOD *sqrt)(IEcoMathC89Ptr_t me, double x);
} IEcoMathC89VTbl;
"""


RESOLVED_COMPONENTS = [
    {
        "name": "Eco.Math.C89",
        "cid": "61C988E21B7041378C5BDAFBB68A3FA0",
        "interface_name": "IEcoMathC89",
        "factory_func": "GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0",
        "header_contents": {
            "IEcoMathC89.h": MATH_HEADER,
            "IdEcoMathC89.h": "extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0;",
        },
    }
]


VALID_ECOMAIN = """
#include "IEcoMathC89.h"
#include "IdEcoMathC89.h"

IEcoInterfaceBus1* g_pIBus = 0;
IEcoMathC89* g_pIMath = 0;

extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0;

int16_t EcoMain(IEcoUnknown* pIUnk) {
#ifdef ECO_LIB
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoInterfaceBus1, (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000042757331);
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoFileSystemManagement1, (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000046534D31);
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoMathC89, (IEcoUnknown*)GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0);
#endif
    return (int16_t)g_pIMath->pVTbl->pow(g_pIMath, 2.0, 10.0);
}
"""


class HeaderParserTests(unittest.TestCase):
    def test_parse_vtbl_methods_extracts_signatures_and_skips_base_methods(self):
        methods = parse_vtbl_methods(MATH_HEADER)

        self.assertEqual([method["name"] for method in methods], ["pow", "sqrt"])
        self.assertEqual(methods[0]["signature"], "double pow(IEcoMathC89Ptr_t me, double x, double y)")

    def test_build_method_map_uses_component_interface_name(self):
        method_map = build_method_map(RESOLVED_COMPONENTS)

        self.assertIn("IEcoMathC89", method_map)
        self.assertEqual({method["name"] for method in method_map["IEcoMathC89"]}, {"pow", "sqrt"})


class VerifierTests(unittest.TestCase):
    def test_verify_ecomain_accepts_valid_code(self):
        errors = verify_ecomain(VALID_ECOMAIN, RESOLVED_COMPONENTS, [])
        self.assertEqual(errors, [])

    def test_verify_ecomain_rejects_unknown_method(self):
        code = VALID_ECOMAIN.replace("->pow(", "->power(")

        errors = verify_ecomain(code, RESOLVED_COMPONENTS, [])

        self.assertTrue(any(error["check"] == "unknown_method" for error in errors))

    def test_verify_ecomain_rejects_direct_call_missing_include_and_eco_os(self):
        code = VALID_ECOMAIN.replace('#include "IEcoMathC89.h"\n', "")
        code = code.replace("->pVTbl->pow(", "->pow(")
        code = "#define ECO_OS\n" + code

        errors = verify_ecomain(code, RESOLVED_COMPONENTS, [])
        checks = {error["check"] for error in errors}

        self.assertIn("missing_include", checks)
        self.assertIn("missing_pvtbl", checks)
        self.assertIn("eco_os_defined", checks)

    def test_verify_ecomain_rejects_wrong_framework_registration_order(self):
        code = VALID_ECOMAIN.replace(
            """    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoInterfaceBus1, (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000042757331);
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoFileSystemManagement1, (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000046534D31);
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoMathC89, (IEcoUnknown*)GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0);
""",
            """    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoMathC89, (IEcoUnknown*)GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0);
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoInterfaceBus1, (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000042757331);
    g_pIBus->pVTbl->RegisterComponent(g_pIBus, &CID_EcoFileSystemManagement1, (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000046534D31);
""",
        )

        errors = verify_ecomain(code, RESOLVED_COMPONENTS, [])

        self.assertTrue(any(error["check"] == "wrong_registration_order" for error in errors))


if __name__ == "__main__":
    unittest.main()
