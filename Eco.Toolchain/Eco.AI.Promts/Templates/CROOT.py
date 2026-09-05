
from eco_python2acom.decorators.server.component import component
from eco_python2acom.decorators.server.factory import export, factory
from eco_python2acom.decorators.server.view import view
from eco_python2acom.guids.gid import GID_IEcoSystem
from eco_python2acom.interfaces.factory import IEcoComponentFactory
from eco_python2acom.interfaces.memory_manager import IEcoMemoryAllocator1
from eco_python2acom.interfaces.system import IEcoSystem1
from eco_python2acom.interfaces.unknown import IEcoUnknown
from eco_python2acom.types.core import Char, CString, Int16, Void
from eco_python2acom.types.errors import EcoErrorCode
from eco_python2acom.types.guid import UGUID
from eco_python2acom.types.helpers import AcquireAllocator
from eco_python2acom.types.pointer import Ptr, pointer
from eco_python2acom.types.utils import byref, cast

from SharedFiles.Id[!output FIX_PROJECT_NAME] import *
from SharedFiles.I[!output FIX_PROJECT_NAME] import *

@component(cid=CID_[!output FIX_PROJECT_NAME])
class C[!output FIX_PROJECT_NAME]:

    system: Ptr[IEcoSystem1]
    mem_alloc: Ptr[IEcoMemoryAllocator1]
    name: Ptr[Char]  # Allocator buffer holding the copied string

    def __eco_new__(self, system: Ptr[IEcoUnknown], outer: Ptr[IEcoUnknown]) -> Int16:
        """Allocation phase — resolve `IEcoSystem1` and reset the owned buffer."""
        self.system = Ptr[IEcoSystem1]()
        self.mem_alloc = Ptr[IEcoMemoryAllocator1]()
        self.name = Ptr[Char]()
        if not bool(system):
            return EcoErrorCode.POINTER

        system_ptr = Ptr[Void]()
        result = system.obj.QueryInterface(byref(GID_IEcoSystem), byref(system_ptr))
        if result != 0 or not bool(system_ptr):
            return EcoErrorCode.NOSYSTEM
        self.system = cast(system_ptr, Ptr[IEcoSystem1])

        return EcoErrorCode.SUCCESS

    def __eco_init__(self, system: Ptr[IEcoUnknown]) -> Int16:
        """Initialisation phase — resolve the memory allocator from the bus."""
        result = AcquireAllocator(self.system, pointer(self.mem_alloc))
        if result != 0 or not bool(self.mem_alloc):
            return EcoErrorCode.GET_MEMORY_ALLOCATOR

        return EcoErrorCode.SUCCESS

    def __eco_del__(self) -> Void:
        """Cleanup phase — free the owned buffer, allocator and system."""
        if bool(self.mem_alloc):
            if bool(self.name):
                self.mem_alloc.obj.Free(cast(self.name, Ptr[Void]))
            self.mem_alloc.obj.Release()
        if bool(self.system):
            self.system.obj.Release()

    @view
    class New(I[!output FIX_PROJECT_NAME]):
        """`I[!output FIX_PROJECT_NAME]` view — single method `MyFunction`."""

        def MyFunction(self, name: CString, copy: Ptr[CString]) -> Int16:
            """Copy the input string into the component and return the copy.

            Args:
                name: Source string.
                copy: Out-parameter receiving a pointer to the copied string.

            Returns:
                0 on success, error code otherwise.
            """
            if not bool(name) or not bool(copy) or not bool(self.mem_alloc):
                return EcoErrorCode.POINTER

            dst = self.mem_alloc.obj.Alloc(len(name) + 1)
            if not bool(dst):
                return EcoErrorCode.OUTOFMEMORY

            buffer = cast(dst, Ptr[Char])
            for idx in range(len(name)):
                buffer[idx] = name[idx : idx + 1]
            buffer[len(name)] = b"\x00"  # NULL terminator

            self.name = buffer
            copy.obj = self.name
            return EcoErrorCode.SUCCESS


@factory(component=C[!output FIX_PROJECT_NAME])
class C[!output FIX_PROJECT_NAME]Factory(IEcoComponentFactory):
    """Factory for `[!output FIX_PROJECT_NAME]."""

    name: CString = b"[!output PROJECT_NAME]"
    version: CString = b"1.0.0.0"
    manufacturer: CString = b"Eco"


singleton, get_component_factory = export(C[!output FIX_PROJECT_NAME]Factory)
