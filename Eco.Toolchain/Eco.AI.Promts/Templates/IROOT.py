from eco_python2acom.decorators.interface import interface
from eco_python2acom.interfaces.unknown import IEcoUnknown
from eco_python2acom.types.core import CString, Int16
from eco_python2acom.types.guid import UGUID
from eco_python2acom.types.pointer import Ptr

IID_I[!output FIX_PROJECT_NAME] = UGUID("[!output GUID_IID]")

@interface(iid=IID_I[!output FIX_PROJECT_NAME])
class I[!output FIX_PROJECT_NAME](IEcoUnknown):
    """`I[!output FIX_PROJECT_NAME]` — minimal demonstration interface."""

    def MyFunction(self, name: CString, copy: Ptr[CString]) -> Int16:
        """Copy the input string and return the copy.

        Args:
            name: Source string.
            copy: Out-parameter receiving a pointer to the copied string.

        Returns:
            0 on success, error code otherwise.
        """
        ...