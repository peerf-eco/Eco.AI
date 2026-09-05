import sys
import os

[!if UNIT_TEST_PROJECT]
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
[!endif]
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 
from eco_python2acom.runtime.system import EcoSystem
from eco_python2acom.types.core import Char, CString, Int16, UInt32, Void
from eco_python2acom.types.guid import UGUID
from eco_python2acom.types.pointer import Ptr
from eco_python2acom.types.utils import byref, cast
from SharedFiles.IdEcoMemoryManager1 import *
from SharedFiles.IEcoMemoryManager1 import *
from SharedFiles.IEcoMemoryAllocator1 import *
[!if UNIT_TEST_PROJECT]
from SharedFiles.Id[!output FIX_PROJECT_NAME] import *
from SharedFiles.I[!output FIX_PROJECT_NAME] import *
[!endif]
[!if ADD_CONNECTION_POINTS]
from SharedFiles.IEcoConnectionPointContainer import *
[!endif]


def main() -> int:

    try:
        print("Initializing EcoSystem...")

        with EcoSystem(lib_dir="") as eco:
            ppvMem = Ptr[Void]()
            result = eco.bus.obj.QueryComponent(
                byref(CID_EcoMemoryManager1), None, byref(IID_IEcoMemoryAllocator1), byref(ppvMem)
            )
            if result != 0 or not bool(ppvMem):
                print(f"Failed to query component (code = {result})\n")
                return -2
            pIMem = cast(ppvMem, Ptr[IEcoMemoryAllocator1])
            print(f"Got {pIMem}")
            name = Ptr[Void]()
            name = pIMem.obj.Alloc(10);
            pIMem.obj.Fill(name, b'a', UInt32(9))
            strName = cast(name, CString) 
            print(f"name = {strName.value.decode('utf-8')}\n")

[!if UNIT_TEST_PROJECT]
            ppv[!output FIX_PROJECT_NAME] = Ptr[Void]()
            result = eco.bus.obj.QueryComponent(byref(CID_[!output FIX_PROJECT_NAME]), None, byref(IID_I[!output FIX_PROJECT_NAME]), byref(ppv[!output FIX_PROJECT_NAME]))
            if result != 0 or not bool(ppv[!output FIX_PROJECT_NAME]):
                print(f"Failed to query component (code = {result})\n")
                return -2
            pI[!output FIX_PROJECT_NAME] = cast(ppv[!output FIX_PROJECT_NAME], Ptr[I[!output FIX_PROJECT_NAME]])

[!if ADD_CONNECTION_POINTS]
            ppvCPC = Ptr[Void]()
            result = pI[!output FIX_PROJECT_NAME].obj.QueryInterface(byref(IID_IEcoConnectionPointContainer), byref(ppvCPC))
            if result != 0 or not bool(ppv[!output FIX_PROJECT_NAME]):
                print(f"Failed to query interface (code = {result})\n")
                return -2
            pICPC = cast(ppvCPC, Ptr[IEcoConnectionPointContainer])

            # Request to get the connection point interface TODO
[!endif]
            copyName = Ptr[Void]()
            result = pI[!output FIX_PROJECT_NAME].obj.MyFunction(name, byref(copyName))
            print(f"copyName = {copyName}\n")
[!endif]
            pIMem.obj.Free(name)
            pIMem.obj.Release()

        print("Released EcoSystem")
        return 0

    except Exception as err:
        print(str(err))
        return -1


if __name__ == "__main__":
    sys.exit(main())
