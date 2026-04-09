#include "SoftkeyYT88.h"
#include "UKey.h"
#include "KeyDef.h"
#include  <math.h>
#define PID 0X8762
#define VID 0X3689
#define PID_NEW 0X2020
#define VID_NEW 0X3689
#define PID_NEW_2 0X2020
#define VID_NEW_2 0X2020

HDEVINFO  ( _stdcall *l_SetupDiGetClassDevsA)(CONST GUID *,   PCSTR , HWND , IN DWORD  );
BOOL   ( _stdcall *l_SetupDiEnumDeviceInterfaces)(HDEVINFO ,PSP_DEVINFO_DATA ,CONST GUID   *,DWORD,PSP_DEVICE_INTERFACE_DATA);
BOOL  ( _stdcall *l_SetupDiGetDeviceInterfaceDetailA)(HDEVINFO ,PSP_DEVICE_INTERFACE_DATA,PSP_DEVICE_INTERFACE_DETAIL_DATA_A ,    DWORD,PDWORD ,PSP_DEVINFO_DATA  );
BOOL  ( _stdcall *l_SetupDiDestroyDeviceInfoList)(HDEVINFO DeviceInfoSet);

void (_stdcall *l_HidD_GetHidGuid) (LPGUID   HidGuid);
BOOLEAN (_stdcall *l_HidD_SetFeature )(HANDLE   HidDeviceObject,PVOID    ReportBuffer,ULONG    ReportBufferLength);
BOOLEAN (_stdcall *l_HidD_GetFeature )(HANDLE   HidDeviceObject,OUT   PVOID    ReportBuffer,ULONG    ReportBufferLength);
BOOLEAN (_stdcall *l_HidD_GetPreparsedData )(HANDLE  HidDeviceObject,OUT   PHIDP_PREPARSED_DATA  * PreparsedData);
BOOLEAN (_stdcall *l_HidD_GetAttributes) (IN  HANDLE HidDeviceObject,OUT PHIDD_ATTRIBUTES    Attributes);
BOOLEAN (__stdcall *l_HidD_FreePreparsedData )(PHIDP_PREPARSED_DATA PreparsedData);
NTSTATUS (__stdcall *l_HidP_GetCaps) (IN  PHIDP_PREPARSED_DATA  PreparsedData,OUT PHIDP_CAPS Capabilities);

SoftkeyYT88::SoftkeyYT88()
{
    IsLoad=LoadLib();
}

SoftkeyYT88::~SoftkeyYT88()
{
    if(hSetApiLib) FreeLibrary(hSetApiLib);
    if(hHidLib) FreeLibrary(hHidLib);
}

int SoftkeyYT88::Hanldetransfe(HANDLE hUsbDevice,BYTE *array_in,int InLen,BYTE *array_out,int OutLen,char *InPath)
{
    BOOL IsU=FALSE;
    if(lstrlenA(InPath)>1)
    {
        if(InPath[5]==':')IsU=TRUE;
    }
    if(IsU)
    {
        //注意，这里inlen要加1
        if(!Ukey_transfer(hUsbDevice,array_in,InLen+1,array_out,OutLen)){
            CloseHandle(hUsbDevice);return -93;
        }
    }
    else
    {
        if(InLen>0)if(!SetFeature(hUsbDevice,array_in,InLen)){CloseHandle(hUsbDevice);return -93;}
        if(OutLen>0)if(!GetFeature(hUsbDevice,array_out,OutLen)){CloseHandle(hUsbDevice);return -94;}
    }
    CloseHandle(hUsbDevice);
    return 0;
}

HANDLE SoftkeyYT88::MyOpenPath(char *InPath)
{
    BOOL biao;int count=0;
    if(strlen(InPath)<1)
    {
        char OutPath[260];
        biao=isfindmydevice(0,&count,OutPath);
        if(!biao){return INVALID_HANDLE_VALUE;}
        return  CreateFileA(OutPath,GENERIC_READ | GENERIC_WRITE,FILE_SHARE_READ | FILE_SHARE_WRITE,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    }
    else
    {
        return  CreateFileA(InPath,GENERIC_READ | GENERIC_WRITE,FILE_SHARE_READ | FILE_SHARE_WRITE,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    }
}


BOOL  SoftkeyYT88::LoadLib()
{
    char SetupApiPath[MAX_PATH*2]="";char HidPath[MAX_PATH*2]="";

    GetSystemDirectoryA(SetupApiPath,MAX_PATH);lstrcatA(SetupApiPath,"\\SetupApi.dll");

    hSetApiLib=LoadLibraryExA(SetupApiPath,NULL,LOAD_WITH_ALTERED_SEARCH_PATH);
    if(hSetApiLib!=NULL)
    {
         l_SetupDiGetClassDevsA=(HDEVINFO ( __stdcall *)(CONST GUID *,   PCSTR , HWND , IN DWORD  ))
                                    GetProcAddress(hSetApiLib,"SetupDiGetClassDevsA");
         l_SetupDiEnumDeviceInterfaces=(BOOL   ( __stdcall *)(HDEVINFO ,PSP_DEVINFO_DATA ,CONST GUID   *,DWORD,PSP_DEVICE_INTERFACE_DATA))
                            GetProcAddress(hSetApiLib,"SetupDiEnumDeviceInterfaces");
         l_SetupDiGetDeviceInterfaceDetailA=(BOOL  ( __stdcall *)(HDEVINFO ,PSP_DEVICE_INTERFACE_DATA,PSP_DEVICE_INTERFACE_DETAIL_DATA_A ,    DWORD,PDWORD ,PSP_DEVINFO_DATA  ))
                            GetProcAddress(hSetApiLib,"SetupDiGetDeviceInterfaceDetailA");
         l_SetupDiDestroyDeviceInfoList=(BOOL  ( __stdcall *)(HDEVINFO DeviceInfoSet))
                        GetProcAddress(hSetApiLib,"SetupDiDestroyDeviceInfoList");

    }
    else
    {
        return FALSE;
    }

    GetSystemDirectoryA(HidPath,MAX_PATH);lstrcatA(HidPath,"\\hid.dll");
    hHidLib=LoadLibraryExA(HidPath,NULL,LOAD_WITH_ALTERED_SEARCH_PATH);
    if(hHidLib!=NULL)
    {
        l_HidD_GetHidGuid=(void (__stdcall *) ( LPGUID  ))
                GetProcAddress(hHidLib,"HidD_GetHidGuid");
        l_HidD_SetFeature=(BOOLEAN (__stdcall *)(HANDLE ,PVOID ,ULONG))
                    GetProcAddress(hHidLib,"HidD_SetFeature");
        l_HidD_GetFeature=(BOOLEAN (__stdcall *)( HANDLE ,PVOID  ,ULONG ))
                    GetProcAddress(hHidLib,"HidD_GetFeature");
        l_HidD_GetPreparsedData=(BOOLEAN (__stdcall *)(HANDLE  ,PHIDP_PREPARSED_DATA  * ))
                    GetProcAddress(hHidLib,"HidD_GetPreparsedData");
        l_HidD_GetAttributes=(BOOLEAN (__stdcall *)(HANDLE  ,PHIDD_ATTRIBUTES  ))
                    GetProcAddress(hHidLib,"HidD_GetAttributes");
        l_HidD_FreePreparsedData=(BOOLEAN (__stdcall *)(PHIDP_PREPARSED_DATA ))
                GetProcAddress(hHidLib,"HidD_FreePreparsedData");
        l_HidP_GetCaps=(NTSTATUS (__stdcall *)(PHIDP_PREPARSED_DATA  ,PHIDP_CAPS  ))
                        GetProcAddress(hHidLib,"HidP_GetCaps");
    }
    else
    {
        return FALSE;
    }
    return TRUE;
}

BOOL SoftkeyYT88::Ukey_transfer(HANDLE hDevice,LPVOID lpInBuffer, int inLen,	LPVOID lpOutBuffer,	int OutLen)
{
    BYTE *dataBuffer=NULL;
    SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER sptdwb;
    ULONG length = 0,returned = 0;
    BOOL status = 0;
    HGLOBAL hglb_1;
    if(inLen>1)
    {

        ZeroMemory(&sptdwb, sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER));
        sptdwb.sptd.Length = sizeof(SCSI_PASS_THROUGH_DIRECT);
        //	sptdwb.sptd.PathId = 0;
        sptdwb.sptd.TargetId = 1;
        //	sptdwb.sptd.Lun = 0;
        sptdwb.sptd.CdbLength = 16;
        sptdwb.sptd.SenseInfoLength = 24;
        sptdwb.sptd.DataIn = SCSI_IOCTL_DATA_OUT;
        sptdwb.sptd.DataTransferLength = inLen;
        sptdwb.sptd.TimeOutValue = 100;
        sptdwb.sptd.DataBuffer = lpInBuffer;
        sptdwb.sptd.SenseInfoOffset =
            offsetof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER,ucSenseBuf);
        //CopyMemory(&sptdwb.sptd.Cdb[0],kcw_p,16);

        // CovertBuf(sptdwb.sptd.Cdb);

        sptdwb.sptd.Cdb[0] = 0xdd;
        sptdwb.sptd.Cdb[1] = 0xfe;                         // Data mode
        sptdwb.sptd.Cdb[3] = (BYTE)inLen;
        sptdwb.sptd.Cdb[4] = (BYTE)(inLen>>8);


        length = sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER);
        status = DeviceIoControl(hDevice,
            IOCTL_SCSI_PASS_THROUGH_DIRECT,
            &sptdwb,
            length,
            &sptdwb,
            length,
            &returned,
            FALSE);
        if((sptdwb.sptd.ScsiStatus != 0) || (status == 0) )return FALSE;
    }

    if(OutLen>0)
    {

        //	dataBuffer=new BYTE[kcw_p->dKCWInLength+5];
        hglb_1=GlobalAlloc(GMEM_ZEROINIT|GMEM_MOVEABLE,OutLen);
        dataBuffer=(BYTE *)LocalLock(hglb_1);
        ZeroMemory(&sptdwb, sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER));
        sptdwb.sptd.Length = sizeof(SCSI_PASS_THROUGH_DIRECT);
        //	sptdwb.sptd.PathId = 0;
        sptdwb.sptd.TargetId = 1;
        //	sptdwb.sptd.Lun = 0;
        sptdwb.sptd.CdbLength = 16;
        sptdwb.sptd.DataIn = SCSI_IOCTL_DATA_IN;
        sptdwb.sptd.SenseInfoLength = 24;
        sptdwb.sptd.DataTransferLength =OutLen ;
        sptdwb.sptd.TimeOutValue = 100;
        sptdwb.sptd.DataBuffer = dataBuffer;
        sptdwb.sptd.SenseInfoOffset =
            offsetof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER,ucSenseBuf);
        //CopyMemory(&sptdwb.sptd.Cdb[0],kcw_p,16);
        sptdwb.sptd.Cdb[0] = 0xd1;
        sptdwb.sptd.Cdb[1] = 0xfe;
        sptdwb.sptd.Cdb[5] = (BYTE)OutLen;
        sptdwb.sptd.Cdb[6] = (BYTE)(OutLen>>8); // 命令
        length = sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER);
        status = DeviceIoControl(hDevice,
            IOCTL_SCSI_PASS_THROUGH_DIRECT,
            &sptdwb,
            length,
            &sptdwb,
            length,
            &returned,
            FALSE);
        if((sptdwb.sptd.ScsiStatus != 0) || (status == 0) ){GlobalUnlock(hglb_1);LocalFree(hglb_1);return FALSE;}
        CopyMemory(lpOutBuffer,dataBuffer,OutLen);
        GlobalUnlock(hglb_1);LocalFree(hglb_1);
        return TRUE;
    }

    return TRUE;
}


int SoftkeyYT88::NT_GetVersion(int *Version,char *InPath)
{
   int ret;
   BYTE array_in[25];BYTE array_out[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   array_in[1]=GETVERSION;
   ret= Hanldetransfe(hUsbDevice,array_in,1,array_out,1,InPath);
   if(ret!=0)return ret;
   *Version=array_out[0];
   return 0x0;
}

int SoftkeyYT88::ReadDword(  DWORD *in_data,char *Path)
{
   BYTE b[4];int result;
   DWORD t[4];
   result= NT_Read(&b[0],&b[1],&b[2],&b[3],Path);
   t[0]=b[0];t[1]=b[1];t[2]=b[2];t[3]=b[3];
   *in_data=t[0]|(t[1]<<8)|(t[2]<<16)|(t[3]<<24);
   return result;
}

int SoftkeyYT88::WriteDword(  DWORD *in_data,char *Path)
{
   BYTE b[4];
   b[0]=(BYTE)*in_data;b[1]=(BYTE)(*in_data>>8);
   b[2]=(BYTE)(*in_data>>16);b[3]=(BYTE)(*in_data>>24);
   return NT_Write(&b[0],&b[1],&b[2],&b[3],Path);
}

int SoftkeyYT88::WriteDword_2(  DWORD *in_data,char *Path)
{
   BYTE b[4];
   b[0]=(BYTE)*in_data;b[1]=(BYTE)(*in_data>>8);
   b[2]=(BYTE)(*in_data>>16);b[3]=(BYTE)(*in_data>>24);
   return NT_Write_2(&b[0],&b[1],&b[2],&b[3],Path);
}

int SoftkeyYT88::NT_Read(  BYTE * ele1,BYTE * ele2,BYTE * ele3,BYTE * ele4,char *Path)
{
   int ret;
   BYTE array_out[25];
   HANDLE hUsbDevice=MyOpenPath(Path);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   ret= Hanldetransfe(hUsbDevice,NULL,0,array_out,4,Path);
   if(ret!=0)return ret;
   *ele1=array_out[0];
   *ele2=array_out[1];
   *ele3=array_out[2];
   *ele4=array_out[3];
   return 0;
}

int SoftkeyYT88::NT_Write(  BYTE * ele1,BYTE * ele2,BYTE * ele3,BYTE * ele4,char *InPath)
{
   int ret;
   BYTE array_in[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   array_in[1]=3;array_in[2]=*ele1;array_in[3]=*ele2;array_in[4]=*ele3;array_in[5]=*ele4;//	array_in[1]=*ele1;array_in[2]=*ele2;
   ret= Hanldetransfe(hUsbDevice,array_in,5,NULL,0,InPath);
   return ret;
}


int SoftkeyYT88::NT_Write_2(  BYTE * ele1,BYTE * ele2,BYTE * ele3,BYTE * ele4,char *InPath)
{
   int ret;
   BYTE array_in[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   array_in[1]=4;array_in[2]=*ele1;array_in[3]=*ele2;array_in[4]=*ele3;array_in[5]=*ele4;//	array_in[1]=*ele1;array_in[2]=*ele2;
   ret= Hanldetransfe(hUsbDevice,array_in,5,NULL,0,InPath);
   return ret;
}

int SoftkeyYT88::NT_FindPort(  int start,char *OutPath)
{
   int count=0;
   ZeroMemory(OutPath,sizeof(OutPath));
   if(isfindmydevice(start,&count,OutPath))return 0;
   return NotFondKey;
}

int SoftkeyYT88::NT_FindPort_2(  int start,DWORD in_data,DWORD verf_data,char *OutPath)
{
   int count=0;
   int pos;DWORD out_data;int ret;
   for(pos=start;pos<127;pos++)
   {
       if(!isfindmydevice(pos,&count,OutPath)){return NotFondKey;}
       ret=WriteDword( &in_data,OutPath);
       if(ret!=0){continue;}
       ret=ReadDword( &out_data,OutPath);
       if(ret!=0){continue;}
       if(out_data==verf_data){return 0;}
   }
   ZeroMemory(OutPath,sizeof(OutPath));
   return NotFondKey;
}

int SoftkeyYT88::Read(BYTE *OutData,short address,BYTE *password,char *Path )
{
    BYTE opcode=0x80;
        int ret;
    BYTE array_in[25],array_out[25];int n;
    HANDLE hUsbDevice=MyOpenPath(Path);
    if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

    if(address>495 || address<0)return ErrAddrOver;
    if(address>255){opcode=0xa0;address=address-256;}

    //array_in[1]要输入的数据长度，array_in[2]要接受的数据长度。array_in[3]指令，
    //array_in[n+3]数据
    array_in[1]=READBYTE;//read 0x10;write 0x11;
    array_in[2]=opcode;//0x01;//read 0x80 ;write 0x40;
    array_in[3]=(BYTE)address;
    for(n=5;n<14;n++)
    {
        array_in[n]=*password;
        password++;
    }
    ret= Hanldetransfe(hUsbDevice,array_in,13,array_out,2,Path);
    if(ret!=0)return ret;
    if(array_out[0]!=0x53 )
    {
        return ErrReadPWD;//表示失败；
    }
    *OutData=array_out[1];
    return 0;
}

 int  SoftkeyYT88::Write(BYTE InData,short address,BYTE *password,char *Path )
{
    BYTE opcode=0x40;int ret;

    BYTE array_in[25],array_out[25];int n;
    HANDLE hUsbDevice=MyOpenPath(Path);
    if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

    if(address>511 || address<0)return ErrAddrOver;
    if(InData<0)return -79;
    if(address>255){opcode=0x60;address=address-256;}

    array_in[1]=WRITEBYTE;//read 0x10;write 0x11;
    array_in[2]=opcode;//0x01;//read 0x80 ;write 0x40;
    array_in[3]=(BYTE)address;
    array_in[4]=InData;
    for(n=5;n<14;n++)
    {
        array_in[n]=*password;
        password++;
    }
    ret= Hanldetransfe(hUsbDevice,array_in,13,array_out,2,Path);
    if(ret!=0)return ret;
    if(array_out[1]!=1 )
    {
        return ErrWritePWD;//表示失败；
    }
    return 0;
}

 int SoftkeyYT88::Y_Read(BYTE *OutData,short address ,short len,BYTE *password,char *Path )
{
    short addr_l,addr_h;int n;int ret;

    BYTE array_in[512],array_out[512];
    HANDLE hUsbDevice=MyOpenPath(Path);
    if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

    if(address>495 || address<0)return ErrAddrOver;
    if( len>255)return -87;
    if(len+address>511)return ErrAddrOver;
    {addr_h=(address>>8)<<1;addr_l=address&0xff;}

    //array_in[1]要输入的数据长度，array_in[2]要接受的数据长度。array_in[3]指令，
    //array_in[n+3]数据
    array_in[1]=YTREADBUF;//read 0x10;write 0x11;
    array_in[2]=(BYTE)addr_h;//0x01;//read 0x80 ;write 0x40;
    array_in[3]=(BYTE)addr_l;
    array_in[4]=(BYTE)len;
    for(n=0;n<8;n++)
    {
        array_in[5+n]=*password;
        password++;
    }
    ret= Hanldetransfe(hUsbDevice,array_in,13,array_out,len+1,Path);
    if(ret!=0)return ret;

    if(array_out[0]!=0x0 )
    {
        return ErrReadPWD;//表示失败；
    }
    for(n=0;n<len;n++)
    {
        *OutData=array_out[n+1];
        OutData++;
    }
    return 0;
}

 int SoftkeyYT88::Y_Write(BYTE *InData,short address,short len,BYTE *password,char *Path )
{
    short addr_l,addr_h;int n;int ret;
    BYTE array_in[512],array_out[512];
    HANDLE hUsbDevice=MyOpenPath(Path);
    if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

    if(len>255)return -87;
    if(address+len-1>511 || address<0)return ErrAddrOver;
    {addr_h=(address>>8)<<1;addr_l=address&0xff;}

    array_in[1]=YTWRITEBUF;//read 0x10;write 0x11;
    array_in[2]=(BYTE)addr_h;//0x01;//read 0x80 ;write 0x40;
    array_in[3]=(BYTE)addr_l;
    array_in[4]=(BYTE )len;
    for(n=0;n<8;n++)
    {
        array_in[5+n]=*password;
        password++;
    }
    for(n=0;n<len;n++)
    {
        array_in[13+n]=*InData;
        InData++;
    }
    ret= Hanldetransfe(hUsbDevice,array_in,13+len,array_out,3,Path);
    if(ret!=0)return ret;

    if(array_out[0]!=0x0)
    {
        return ErrWritePWD;//表示失败；
    }
    return 0;
}

BOOL SoftkeyYT88::isfindmydevice( int pos ,int *count,char *OutPath)
{

   HDEVINFO                            hardwareDeviceInfo=NULL;
   SP_INTERFACE_DEVICE_DATA            deviceInfoData;
   ULONG                               i;
   GUID                                hidGuid;
   PSP_INTERFACE_DEVICE_DETAIL_DATA_A    functionClassDeviceData = NULL;
   ULONG                               predictedLength = 0;
   ULONG                               requiredLength = 0;
   HANDLE                              d_handle;
   HIDD_ATTRIBUTES                    Attributes;

   if(!LoadLib())return FALSE;
   *count=0;

   (*l_HidD_GetHidGuid) (&hidGuid);

   hardwareDeviceInfo = (  *l_SetupDiGetClassDevsA ) ( &hidGuid,
                                              NULL, // Define no enumerator (global)
                                              NULL, // Define no
                                              DIGCF_PRESENT | DIGCF_DEVICEINTERFACE); // Function class devices.

  if(hardwareDeviceInfo==INVALID_HANDLE_VALUE)
  {
      return FALSE;
  }
   deviceInfoData.cbSize = sizeof (SP_INTERFACE_DEVICE_DATA);

       for (i=0; (*l_SetupDiEnumDeviceInterfaces) (hardwareDeviceInfo,0,&hidGuid,i,&deviceInfoData); i++)
       {
               if (ERROR_NO_MORE_ITEMS == GetLastError()) break;
               (*l_SetupDiGetDeviceInterfaceDetailA) (hardwareDeviceInfo,&deviceInfoData,NULL,
                       0,&requiredLength,NULL);
               predictedLength = requiredLength;
               functionClassDeviceData =(SP_INTERFACE_DEVICE_DETAIL_DATA_A *) malloc (predictedLength);
               if (functionClassDeviceData)
               {
#ifdef _WIN64
                   functionClassDeviceData->cbSize = sizeof (SP_INTERFACE_DEVICE_DETAIL_DATA_A);
#else
                   functionClassDeviceData->cbSize = 5;
#endif
               }
               else
               {
                   (*l_SetupDiDestroyDeviceInfoList) (hardwareDeviceInfo);
                   return FALSE;
               }

               if (! (*l_SetupDiGetDeviceInterfaceDetailA) (hardwareDeviceInfo,&deviceInfoData,functionClassDeviceData,
                          predictedLength,&requiredLength,NULL))
               {
                   free( functionClassDeviceData);
                   (*l_SetupDiDestroyDeviceInfoList) (hardwareDeviceInfo);
                   return FALSE;
               }
                d_handle = CreateFileA (functionClassDeviceData->DevicePath,  GENERIC_READ | GENERIC_WRITE,FILE_SHARE_READ | FILE_SHARE_WRITE,NULL, OPEN_EXISTING, 0,  NULL);
                if (INVALID_HANDLE_VALUE != d_handle)
                {
                    if ((*l_HidD_GetAttributes) (d_handle, &Attributes))
                    {
                        if(((Attributes.ProductID==PID) && (Attributes.VendorID==VID)) ||
                            ((Attributes.ProductID==PID_NEW) && (Attributes.VendorID==VID_NEW)) ||
                               ((Attributes.ProductID==PID_NEW_2) && (Attributes.VendorID==VID_NEW_2)))
                           {
                                   if(pos==*count)
                                   {
                                       lstrcpyA(OutPath,functionClassDeviceData->DevicePath);
                                       free(functionClassDeviceData);
                                       (*l_SetupDiDestroyDeviceInfoList) (hardwareDeviceInfo);
                                        CloseHandle(d_handle);
                                       return TRUE;
                                   }
                                   (*count)++;
                           }
                   }
                    CloseHandle(d_handle);
                }
               free(functionClassDeviceData);
           }
   (*l_SetupDiDestroyDeviceInfoList) (hardwareDeviceInfo);
   return FALSE;

}


BOOL SoftkeyYT88::SetFeature (HANDLE hDevice,BYTE *array_in,INT in_len)
/*++
RoutineDescription:
Given a struct _HID_DEVICE, take the information in the HID_DATA array
pack it into multiple reports and send it to the hid device via HidD_SetFeature()
--*/
{

   PHIDP_PREPARSED_DATA Ppd;
   HIDP_CAPS            Caps;
    BOOLEAN   Status;
   BOOLEAN   FeatureStatus;
   DWORD     ErrorCode;
   INT		  i;
   BYTE FeatureReportBuffer[512];

   if (!(*l_HidD_GetPreparsedData) (hDevice, &Ppd)) return FALSE;

   if (!(*l_HidP_GetCaps) (Ppd, &Caps))
   {
           (*l_HidD_FreePreparsedData)(Ppd);
           return FALSE;
   }

   Status = TRUE;

   FeatureReportBuffer[0]=0x02;

   array_in++;
   for(i=1;i<=in_len;i++)
   {
       FeatureReportBuffer[i]=*array_in;
       array_in++;
   }
   FeatureStatus =((*l_HidD_SetFeature)(hDevice,
                                 FeatureReportBuffer,
                                 Caps.FeatureReportByteLength));

   ErrorCode = GetLastError();

   Status = Status && FeatureStatus;
   (*l_HidD_FreePreparsedData)(Ppd);
   return (Status);
}

BOOL SoftkeyYT88::GetFeature (HANDLE hDevice,BYTE *array_out,INT out_len)
/*++
RoutineDescription:
  Given a struct _HID_DEVICE, fill in the feature data structures with
  all features on the device.  May issue multiple HidD_GetFeature() calls to
  deal with multiple report IDs.
--*/
{
  // ULONG     Index;
   BOOLEAN   FeatureStatus;
   BOOLEAN   Status;
   INT		  i;
   BYTE      FeatureReportBuffer[512];
   PHIDP_PREPARSED_DATA Ppd;
   HIDP_CAPS            Caps;
   if (!(*l_HidD_GetPreparsedData) (hDevice, &Ppd)) return FALSE;

   if (!(*l_HidP_GetCaps) (Ppd, &Caps))
   {
           (*l_HidD_FreePreparsedData)(Ppd);
           return FALSE;
   }
   /*
   // As with writing data, the IsDataSet value in all the structures should be
   //    set to FALSE to indicate that the value has yet to have been set
   */
   Status = TRUE;

   memset(FeatureReportBuffer, 0x00, 512);

   FeatureReportBuffer[0] = 0x01;

   FeatureStatus = (*l_HidD_GetFeature) (hDevice,
                                     FeatureReportBuffer,
                                     Caps.FeatureReportByteLength);
   if (FeatureStatus)
   {

       if(FeatureStatus)
       {
           for(i=0;i<out_len;i++)
           {
               *array_out=FeatureReportBuffer[i];
               array_out++;
           }
       }
   }

   Status = Status && FeatureStatus;
   (*l_HidD_FreePreparsedData)(Ppd);

  return (Status);
}


int SoftkeyYT88::NT_GetID(  DWORD *ID_1,DWORD *ID_2,char *InPath)
{
       DWORD t[8];int ret;
   BYTE array_in[25];BYTE array_out[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   array_in[1]=GETID;
   ret= Hanldetransfe(hUsbDevice,array_in,1,array_out,8,InPath);
   if(ret!=0)return ret;
   t[0]=array_out[0];t[1]=array_out[1];t[2]=array_out[2];t[3]=array_out[3];
   t[4]=array_out[4];t[5]=array_out[5];t[6]=array_out[6];t[7]=array_out[7];
   *ID_1=t[3]|(t[2]<<8)|(t[1]<<16)|(t[0]<<24);
   *ID_2=t[7]|(t[6]<<8)|(t[5]<<16)|(t[4]<<24);
   return 0;
}

int SoftkeyYT88::NT_Cal(  BYTE * InBuf,BYTE *OutBuf,char *InPath)
{
   int n;int ret;
   BYTE array_in[25];BYTE array_out[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   array_in[1]=CAL_TEA;
   for (n=2;n<10;n++)
   {
       array_in[n]=InBuf[n-2];
   }
   ret= Hanldetransfe(hUsbDevice,array_in,9,array_out,10,InPath);
   if(ret!=0)return ret;
   memcpy(OutBuf,array_out,8);
   if(array_out[8]!=0x55)
   {
       return ErrResult;
   }
   return 0;
}

int SoftkeyYT88::NT_SetCal_2(BYTE *InData,BYTE IsHi,char *Path )
{
      int n;int ret;
      BYTE array_in[30],array_out[25];
      BYTE opcode=SET_TEAKEY;
      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_in[1]=opcode;
      array_in[2]=IsHi;
      for(n=0;n<8;n++)
      {
          array_in[3+n]=*InData;
          InData++;
      }
      ret= Hanldetransfe(hUsbDevice,array_in,11,array_out,3,Path);
      if(ret!=0)return ret;
      if(array_out[0]!=0x0)
      {
          return ErrResult;//表示失败；
      }
      return 0;
}

int SoftkeyYT88::NT_ReSet(char *Path )
{

       int ret;
      BYTE array_in[30],array_out[25];
      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
      array_in[1]=MYRESET;
      ret= Hanldetransfe(hUsbDevice,array_in,2,array_out,1,Path);
      if(ret!=0)return ret;
      if(ret!=0)return ret;
      if(array_out[0]!=0x0)
      {
          return ErrResult;//表示失败；
      }
      return 0;
}

int SoftkeyYT88::NT_SetID(  BYTE * InBuf,char *InPath)
{
  int n,ret;
  BYTE array_in[25];BYTE array_out[25];
  HANDLE hUsbDevice=MyOpenPath(InPath);
  if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
  array_in[1]=SETID;
  for (n=2;n<10;n++)
  {
      array_in[n]=InBuf[n-2];
  }
  ret=Hanldetransfe(hUsbDevice,array_in,9,array_out,1,InPath);
  if(ret!=0)return ret;
  if(array_out[0]!=0x0)
  {
       return ErrResult;//表示失败；
  }
  return 0;
}

int  SoftkeyYT88::NT_GetProduceDate(  BYTE *OutDate,char *InPath)
{
       int ret;
    BYTE array_in[25];
    HANDLE hUsbDevice=MyOpenPath(InPath);
    if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
    array_in[1]=GETSN;
    ret= Hanldetransfe(hUsbDevice,array_in,1,OutDate,8,InPath);
    return ret;
}

int  SoftkeyYT88::F_GetVerEx(int *Version,char *InPath)
{
       int ret;
   BYTE array_in[25];BYTE array_out[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

   array_in[1]=GETVEREX;
   ret= Hanldetransfe(hUsbDevice,array_in,1,array_out,1,InPath);
   if(ret!=0)return ret;
   *Version=array_out[0];
   return 0x0;
}


int SoftkeyYT88::NT_Cal_New(  BYTE * InBuf,BYTE *OutBuf,char *InPath)
{
   int n,ret;
   BYTE array_in[25];BYTE array_out[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

   array_in[1]=CAL_TEA_2;
   for (n=2;n<10;n++)
   {
       array_in[n]=InBuf[n-2];
   }
   ret= Hanldetransfe(hUsbDevice,array_in,9,array_out,10,InPath);
   if(ret!=0)return ret;
   memcpy(OutBuf,array_out,8);
   if(array_out[8]!=0x55)
   {
       return ErrResult;
   }

   return 0;
}

int SoftkeyYT88::NT_SetCal_New(BYTE *InData,BYTE IsHi,char *Path )
{
    int n,ret;
    BYTE array_in[30],array_out[25];
    BYTE opcode=SET_TEAKEY_2;
    HANDLE hUsbDevice=MyOpenPath(Path);
    if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

    array_in[1]=opcode;
    array_in[2]=IsHi;
    for(n=0;n<8;n++)
    {
      array_in[3+n]=*InData;
      InData++;
    }
    ret= Hanldetransfe(hUsbDevice,array_in,11,array_out,3,Path);
    if(ret!=0)return ret;
    if(array_out[0]!=0x0)
    {
        return ErrResult;//表示失败；
    }
    return 0;
}

int SoftkeyYT88::NT_Set_SM2_KeyPair(BYTE *PriKey,BYTE *PubKeyX,BYTE *PubKeyY,char *sm2UserName,char *Path )
{

      int ret;
      BYTE array_in[256],array_out[25];

      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
      memset(array_in,0,256);

      array_in[1]=SET_ECC_KEY;
      memcpy(&array_in[2+ECC_MAXLEN*0],PriKey,ECC_MAXLEN);
      memcpy(&array_in[2+ECC_MAXLEN*1],PubKeyX,ECC_MAXLEN);
      memcpy(&array_in[2+ECC_MAXLEN*2],PubKeyY,ECC_MAXLEN);
      if(sm2UserName!=0)
      {
          memcpy(&array_in[2+ECC_MAXLEN*3],sm2UserName,USERID_LEN);
      }
      ret= Hanldetransfe(hUsbDevice,array_in,ECC_MAXLEN*3+2+USERID_LEN,array_out,1,Path);
      if(ret!=0)return ret;
      if(array_out[0]!=0x20)return USBStatusFail;

      return 0;
}

int SoftkeyYT88::NT_Get_SM2_PubKey(BYTE *KGx,BYTE *KGy,char *sm2UserName,char *Path )
{

      int ret;
      BYTE array_in[256],array_out[256];
      HANDLE hUsbDevice=MyOpenPath(Path);
      array_out[0]=0xfb;
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_in[1]=GET_ECC_KEY;
      ret= Hanldetransfe(hUsbDevice,array_in,2,array_out,ECC_MAXLEN*2+2+USERID_LEN,Path);
      if(ret!=0)return ret;

      if(array_out[0]!=0x20)return USBStatusFail;
      memcpy(KGx,&array_out[1+ECC_MAXLEN*0],ECC_MAXLEN);
      memcpy(KGy,&array_out[1+ECC_MAXLEN*1],ECC_MAXLEN);
      memcpy(sm2UserName,&array_out[1+ECC_MAXLEN*2],USERID_LEN);

      return 0;
}


int SoftkeyYT88::NT_GenKeyPair(BYTE* PriKey,BYTE *PubKey,char *Path )
{

      int ret;
      BYTE array_in[256],array_out[256];
      HANDLE hUsbDevice=MyOpenPath(Path);
      array_out[0]=0xfb;
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_in[1]=GEN_KEYPAIR;
      ret= Hanldetransfe(hUsbDevice,array_in,2,array_out,ECC_MAXLEN*3+2,Path);
      if(ret!=0)return ret;

      if(array_out[0]!=0x20)
      {
          return FAILEDGENKEYPAIR;//表示读取失败；
      }
      memcpy(PriKey,&array_out[1+ECC_MAXLEN*0],ECC_MAXLEN);
      memcpy(PubKey,&array_out[1+ECC_MAXLEN*1],ECC_MAXLEN*2+1);
      return 0;
}

int SoftkeyYT88::NT_Set_Pin(char *old_pin,char *new_pin,char *Path )
{

      int ret;
      BYTE array_in[256],array_out[25];
      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_in[1]=SET_PIN;
      memcpy(&array_in[2+PIN_LEN*0],old_pin,PIN_LEN);
      memcpy(&array_in[2+PIN_LEN*1],new_pin,PIN_LEN);

      ret= Hanldetransfe(hUsbDevice,array_in,PIN_LEN*2+2,array_out,2,Path);
      if(ret!=0)return ret;

      if(array_out[0]!=0x20)return USBStatusFail;
      if(array_out[1]!=0x20)return FAILPINPWD;
      return 0;
}


int SoftkeyYT88::NT_SM2_Enc(BYTE *inbuf,BYTE *outbuf,BYTE inlen,char *Path )
{

      int n;int ret;
      BYTE array_in[256],array_out[256];

      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_out[0]=0xfb;
      array_in[1]=MYENC;
      array_in[2]=inlen;
      for(n=0;n<inlen;n++)
      {
        array_in[3+n]=inbuf[n];
      }
      ret= Hanldetransfe(hUsbDevice,array_in,inlen+1+2,array_out,inlen+SM2_ADDBYTE+3,Path);
      if(ret!=0)return ret;

      if(array_out[0]!=0x20)return USBStatusFail;
      if(array_out[1]==0)return FAILENC;

      memcpy(outbuf,&array_out[2],inlen+SM2_ADDBYTE);

      return 0;
}

int SoftkeyYT88::NT_SM2_Dec(BYTE *inbuf,BYTE *outbuf,BYTE inlen,char* pin,char *Path )
{

      int n;int ret;
      BYTE array_in[256],array_out[256];

      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_out[0]=0xfb;
      array_in[1]=MYDEC;
      memcpy(&array_in[2],pin,PIN_LEN);
      array_in[2+PIN_LEN]=inlen;
      for(n=0;n<inlen;n++)
      {
        array_in[2+PIN_LEN+1+n]=inbuf[n];
      }
      ret= Hanldetransfe(hUsbDevice,array_in,inlen+1+2+PIN_LEN,array_out,inlen-SM2_ADDBYTE+4,Path);
      if(ret!=0)return ret;

      if(array_out[2]!=0x20)return FAILPINPWD;
      if(array_out[1]==0) return FAILENC;
      if(array_out[0]!=0x20)return USBStatusFail;
      memcpy(outbuf,&array_out[3],inlen-SM2_ADDBYTE);

      return 0;
}

int SoftkeyYT88::NT_Sign(BYTE *inbuf,BYTE *outbuf,char* pin,char *Path )
{

      int n;int ret;
      BYTE array_in[256],array_out[256];
      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_out[0]=0xfb;
      array_in[1]=YTSIGN;
      memcpy(&array_in[2],pin,PIN_LEN);
      for(n=0;n<32;n++)
      {
        array_in[2+PIN_LEN+n]=inbuf[n];
      }
      ret= Hanldetransfe(hUsbDevice,array_in,32+2+PIN_LEN,array_out,64+2,Path);
      if(ret!=0)return ret;

      if(array_out[1]!=0x20)return FAILPINPWD;
      if(array_out[0]!=0x20)return USBStatusFail;
      memcpy(outbuf,&array_out[2],64);

      return 0;
}

int SoftkeyYT88::NT_Sign_2(BYTE *inbuf,BYTE *outbuf,char* pin,char *Path )
{

      int n;int ret;
      BYTE array_in[256],array_out[256];
      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_out[0]=0xfb;
      array_in[1]=YTSIGN_2;
      memcpy(&array_in[2],pin,PIN_LEN);
      for(n=0;n<32;n++)
      {
        array_in[2+PIN_LEN+n]=inbuf[n];
      }
      ret= Hanldetransfe(hUsbDevice,array_in,32+2+PIN_LEN,array_out,64+2,Path);
      if(ret!=0)return ret;
      if(array_out[1]!=0x20)return FAILPINPWD;
      if(array_out[0]!=0x20)return USBStatusFail;
      memcpy(outbuf,&array_out[2],64);

      return 0;
}

int SoftkeyYT88::NT_Verfiy(BYTE *inbuf,BYTE *InSignBuf,BOOL *outbiao,char *Path )
{

      int n;int ret;
      BYTE array_in[256],array_out[256];
      HANDLE hUsbDevice=MyOpenPath(Path);
      if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;

      array_out[0]=0xfb;
      array_in[1]=YTVERIFY;
      for(n=0;n<32;n++)
      {
        array_in[2+n]=inbuf[n];
      }
      for(n=0;n<64;n++)
      {
        array_in[2+32+n]=InSignBuf[n];
      }
      ret= Hanldetransfe(hUsbDevice,array_in,32+2+64,array_out,3,Path);
      if(ret!=0)return ret;
      *outbiao=array_out[1];
      if(array_out[0]!=0x20)return USBStatusFail;

      return 0;
}

int  SoftkeyYT88::NT_GetChipID(  BYTE *OutChipID,char *InPath)
{
   int ret;
   BYTE array_in[25];BYTE array_out[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   array_in[1]=GET_CHIPID;
   ret= Hanldetransfe(hUsbDevice,array_in,1,array_out,17,InPath);
   if(ret!=0)return ret;
   if(array_out[0]!=0x20)return USBStatusFail;
   memcpy(OutChipID,&array_out[1],16);

   return 0;
}

int SoftkeyYT88::Sub_SetOnly(BOOL IsOnly,BYTE Flag,char *InPath)
{
   int ret;
   BYTE array_in[25];BYTE array_out[25];
   HANDLE hUsbDevice=MyOpenPath(InPath);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   array_in[1]=Flag;
   if(IsOnly)array_in[2]=0;else array_in[2]=0xff;
   ret=Hanldetransfe(hUsbDevice,array_in,3,array_out,1,InPath);
   if(ret!=0)return ret;
   if(array_out[0]!=0x0)
   {
       return ErrResult;//表示失败；
   }
   return 0;
}

int SoftkeyYT88::NT_SetHidOnly(  BOOL IsHidOnly,char *InPath)
{
   return Sub_SetOnly(IsHidOnly,SETHIDONLY,InPath);
}

int  SoftkeyYT88::NT_SetUReadOnly(char *InPath)
{
   return Sub_SetOnly(TRUE,SETREADONLY,InPath);
}

int SoftkeyYT88::GetTrashBufLen(char * Path,int *OutLen)
{
   PHIDP_PREPARSED_DATA Ppd;
   HIDP_CAPS            Caps;
   HANDLE hUsbDevice=MyOpenPath(Path);
   if(hUsbDevice == INVALID_HANDLE_VALUE)return NotFondKey;
   if (!(*l_HidD_GetPreparsedData) (hUsbDevice, &Ppd)) return ErrSendData;
   if (!(*l_HidP_GetCaps) (Ppd, &Caps))
   {
       (*l_HidD_FreePreparsedData)(Ppd);
       return ErrSendData;
   }
   CloseHandle(hUsbDevice);
   *OutLen=Caps.FeatureReportByteLength-5;
    (*l_HidD_FreePreparsedData)(Ppd);
   return 0;
}

int SoftkeyYT88::NT_GetIDVersion(int *Version,char *InPath)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_GetVersion)(Version,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::GetID(  DWORD *ID_1,DWORD *ID_2,char *InPath)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_GetID)(ID_1,ID_2,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::sRead(  DWORD *in_data,char *Path)
{
    int ret;
    //////////////////////////////////////////////////////////////////////////////////

    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(ReadDword)(in_data,Path);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::sWrite(  DWORD out_data,char *Path)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(WriteDword)(&out_data,Path);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::YWrite(BYTE InData,short address,char * HKey,char *LKey,char *Path )
{
    if(address>495){return  -81;}
    BYTE ary1[8];
    myconvert(HKey,LKey,ary1);
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(Write)(InData,address,ary1,Path);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

 int SoftkeyYT88::YRead(BYTE *OutData,short address,char * HKey,char *LKey,char *Path )
{
    if(address>495){return  -81;}
    BYTE ary1[8];
    myconvert(HKey,LKey,ary1);
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(Read)(OutData,address,ary1,Path);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::YWriteEx(BYTE *InData,short Address,short len,char *HKey,char *LKey,char *Path )
{
    int ret;BYTE password[8];int n,trashLen;int temp_leave, leave; HANDLE hsignal;
     if(Address+len-1>495 || Address<0)return -81;

     ret=GetTrashBufLen(Path,&trashLen);
     trashLen=trashLen-8;
     if(ret!=0)return ret;

     myconvert(HKey,LKey,password);

     hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");

     WaitForSingleObject(hsignal,INFINITE);
     temp_leave=Address-Address/trashLen*trashLen; leave=trashLen-temp_leave;
     if(leave>len){leave=len;}
     if(leave>0)
     {
         for(n=0;n<leave/trashLen;n++)
         {
             ret=(Y_Write)(InData+n*trashLen,Address+n*trashLen,trashLen,password,Path);
             if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);return  ret;}
         }
         if(leave-trashLen*n>0)
         {
             ret=(Y_Write)(InData+n*trashLen,Address+n*trashLen,(BYTE)(leave-n*trashLen),password,Path);
             if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);return  ret;}

         }
     }
     len=len-leave;Address=Address+leave;InData=InData+leave;
     if (len>0)
     {
         for(n=0;n<len/trashLen;n++)
         {
             ret=(Y_Write)(InData+n*trashLen,Address+n*trashLen,trashLen,password,Path);
             if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);return ret;}
         }
         if(len-trashLen*n>0)
         {
             ret=(Y_Write)(InData+n*trashLen,Address+n*trashLen,(BYTE)(len-n*trashLen),password,Path);
             if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);return ret;}

         }
     }
     ReleaseSemaphore(hsignal,1,NULL);
     CloseHandle(hsignal);
     return ret;
}

int SoftkeyYT88::YReadEx(BYTE *OutData,short Address,short len,char *HKey,char *LKey,char *Path )
{
    int ret;BYTE password[8];int n,trashLen; HANDLE hsignal;
    if(Address+len-1>495 || Address<0)return -81;

    ret=GetTrashBufLen(Path,&trashLen);
    if(ret!=0)return ret;

   myconvert(HKey,LKey,password);

    hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    for(n=0;n<len/trashLen;n++)
    {
        ret=(Y_Read)(OutData+n*trashLen,Address+n*trashLen,trashLen,password,Path);
        if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);return ret;}
    }
    if(len-trashLen*n>0)
    {
        ret=(Y_Read)(OutData+n*trashLen,Address+n*trashLen,(len-trashLen*n),password,Path);
        if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);return ret;}

    }
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::FindPort_2(  int start,DWORD in_data,DWORD verf_data,char *OutPath)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_FindPort_2)(start,in_data,verf_data,OutPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::FindPort(  int start,char *OutPath)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_FindPort)(start,OutPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::sWrite_2(  DWORD out_data,char *Path)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(WriteDword_2)(&out_data,Path);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

VOID SoftkeyYT88::myconvert(char *hkey,char *lkey,BYTE *out_data)
{
    DWORD z,z1;int n;
    z=HexToInt(hkey);
    z1=HexToInt(lkey);
    for(n=0;n<=3;n++)
    {
        *out_data=(BYTE)((z<<(n*8))>>24);
        out_data++;
    }
    for(n=0;n<=3;n++)
    {
        *out_data=(BYTE)((z1<<(n*8))>>24);
        out_data++;
    }
}

DWORD SoftkeyYT88::HexToInt(char* s)
{
    char hexch[] = "0123456789ABCDEF";
    size_t i;
   DWORD r,n,k,j;
   char ch;

    k=1; r=0;
    for (i=strlen(s);  i>0; i--) {
    ch = s[i-1]; if (ch > 0x3f) ch &= 0xDF;
    n = 0;
        for (j = 0; j<16; j++)
        if (ch == hexch[j])
            n = j;
        r += (n*k);
        k *= 16;
    }
    return r;
}

int SoftkeyYT88::SetReadPassword(char * W_HKey,char *W_LKey,char * new_HKey,char *new_LKey,char *InPath)
{

    BYTE ary1[8];BYTE ary2[8];
    myconvert(W_HKey,W_LKey,ary1);
    myconvert(new_HKey,new_LKey,ary2);
    int ret;int address=0x1f0;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(Y_Write)(ary2,address,8,ary1,InPath);
    if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);return ret;}
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}


int SoftkeyYT88::SetWritePassword(char * W_HKey,char *W_LKey,char * new_HKey,char *new_LKey,char *InPath)
{
    BYTE ary1[8];BYTE ary2[8];
    myconvert(W_HKey,W_LKey,ary1);
    myconvert(new_HKey,new_LKey,ary2);
    int ret;int address=0x1f8;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(Y_Write)(ary2,address,8,ary1,InPath);
    if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);return ret;}
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

int SoftkeyYT88::YWriteString(char *InString,short Address,char * HKey,char *LKey,char *Path )
{
    BYTE ary1[8];int n,trashLen;int ret=0,outlen,total_len;HANDLE hsignal;//int versionex;

    ret=GetTrashBufLen(Path,&trashLen);
    trashLen=trashLen-8;
    if(ret!=0)return ret;

    myconvert(HKey,LKey,ary1);

    outlen=lstrlenA(InString);
    total_len=Address+outlen;
    if(total_len>495){return -47;}

    hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    {
        WaitForSingleObject(hsignal,INFINITE);
        for(n=0;n<outlen/trashLen;n++)
        {
            ret=(Y_Write)((BYTE *)(InString+n*trashLen),Address+n*trashLen,trashLen,ary1,Path);
            if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);return  ret;}
        }
        if(outlen-trashLen*n>0)
        {
            ret=(Y_Write)((BYTE *)(InString+n*trashLen),Address+n*trashLen,(BYTE)(outlen-n*trashLen),ary1,Path);
            if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);return  ret;}

        }
        ReleaseSemaphore(hsignal,1,NULL);
    }
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::YReadString(char *string ,short Address,int len,char * HKey,char *LKey,char *Path )
{
    BYTE ary1[8];int n,trashLen;int ret=0;HANDLE hsignal;int total_len;//DWORD z,z1;int versionex;

        ret=GetTrashBufLen(Path,&trashLen);
        if(ret!=0)return ret;

        myconvert(HKey,LKey,ary1);

        total_len=Address+len;
        if(total_len>495){return -47;}

        hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
        {
            WaitForSingleObject(hsignal,INFINITE);
            for(n=0;n<len/trashLen;n++)
            {
                ret=(Y_Read)((BYTE*)(string+n*trashLen),Address+n*trashLen,trashLen,ary1,Path);
                if(ret!=0)
                {
                    ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);
                    return ret;
                }
            }
            if(len-trashLen*n>0)
            {
                ret=(Y_Read)((BYTE*)(string+n*trashLen),Address+n*trashLen,(len-trashLen*n),ary1,Path);
                if(ret!=0)
                {
                    ReleaseSemaphore(hsignal,1,NULL);CloseHandle(hsignal);
                    return ret;
                }

            }
            ReleaseSemaphore(hsignal,1,NULL);
        }
        CloseHandle(hsignal);
        return ret;
}

 void SoftkeyYT88::ByteArrayToHexString(BYTE *in_data,char * OutString,int len)
{
    memset(OutString,0,len*2);
    char temp[5];int n;
    for (n=1;n<=len;n++)
    {
        wsprintfA(temp,"%02X",*in_data);
        in_data++;
        lstrcatA(OutString,temp);
    }
}

 VOID SoftkeyYT88::HexStringToByteArray(char * InString,BYTE *in_data)
{
    int len=lstrlenA(InString);
    char temp[5];int n;
    for (n=1;n<=len;n=n+2)
    {
        ZeroMemory(temp,sizeof(temp));
        lstrcpynA(temp,&InString[n-1],2+1);
        *in_data=(BYTE)HexToInt(temp);
        in_data++;
    }
}

 void SoftkeyYT88::HexStringToByteArrayEx(char * InString,BYTE *in_data)
{
    int len=lstrlenA(InString);
    char temp[5];int n;
    if(len>32)len=32;
    for (n=1;n<=len;n=n+2)
    {
        ZeroMemory(temp,sizeof(temp));
        lstrcpynA(temp,&InString[n-1],2+1);
        *in_data=(BYTE)HexToInt(temp);
        in_data++;
    }

}

int SoftkeyYT88::SetCal_2(char *Key,char *InPath)
{
    BYTE KeyBuf[16];
    memset(KeyBuf,0,16);
    HexStringToByteArrayEx(Key,KeyBuf);
    //注意，这里是地址互换的
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_SetCal_2)(&KeyBuf[8],0,InPath);
    if(ret!=0)goto error1;
    ret=(NT_SetCal_2)(&KeyBuf[0],1,InPath);
error1:
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

int SoftkeyYT88::Cal(  BYTE *InBuf,BYTE *OutBuf,char *Path)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=NT_Cal(InBuf,OutBuf,Path);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::GetLen(char *InString)
{
    return lstrlenA(InString)+1;
}

int SoftkeyYT88::EncString(  char *InString,char *OutString,char *Path)
{

    int ret;int n;BYTE *outbuf;
    int len=lstrlenA(InString)+1;if(len<8)len=8;
    outbuf=new BYTE[len];
    memset(outbuf,0,len);
    memcpy(outbuf,InString,lstrlenA(InString)+1);
    for(n=0;n<=(len-8);n=n+8)
    {
        ret=Cal((BYTE *)&outbuf[n],&outbuf[n],Path);
        if(ret!=0){delete [] outbuf;return ret;}
    }
    ByteArrayToHexString(outbuf,OutString,len);
    delete [] outbuf;
    return ret;
}

void SoftkeyYT88:: EncBySoft(   BYTE  *   aData,  BYTE   *   aKey   )
{
    const   unsigned   long   cnDelta   =   0x9E3779B9;
    register   unsigned   long   y   =   (   (   unsigned   long   *   )aData   )[0],   z   =   (   (   unsigned   long   *   )aData   )[1];
    register   unsigned   long   sum   =   0;
    unsigned   long   a   =   (   (   unsigned   long   *   )aKey   )[0],   b   =   (   (   unsigned   long   *   )aKey   )[1];
    unsigned   long   c   =   (   (   unsigned   long   *   )aKey   )[2],   d   =   (   (   unsigned   long   *   )aKey   )[3];
    int   n   =   32;

    while   (   n--   >   0   )
    {
        sum   +=   cnDelta;
        y   +=   ((   z   <<   4   )   +   a )  ^   (z   +   sum )  ^  ( (   z   >>   5   )   +   b);

        z   +=   ((   y   <<   4   )   +   c )  ^   (y   +   sum )  ^  ( (   y   >>   5   )   +   d);
    }
    (   (   unsigned   long   *   )aData   )[0]   =   y;
    (   (   unsigned   long   *   )aData   )[1]   =   z;
}

void SoftkeyYT88:: DecBySoft(    BYTE  *   aData,   BYTE   *   aKey   )
{
    const   unsigned   long   cnDelta   =   0x9E3779B9;
    register   unsigned   long   y   =   (   (   unsigned   long   *   )aData   )[0],   z   =   (   (   unsigned   long   *   )aData   )[1];
    register   unsigned   long   sum   =   0xC6EF3720;
    unsigned   long   a   =   (   (   unsigned   long   *   )aKey   )[0],   b   =   (   (   unsigned   long   *   )aKey   )[1];
    unsigned   long   c   =   (   (   unsigned   long   *   )aKey   )[2],   d   =   (   (   unsigned   long   *   )aKey   )[3];
    int   n   =   32;
    while   (   n--   >   0   )
    {
        z   -=  ( (   y   <<   4   )   +   c )  ^  ( y   +   sum  ) ^ (  (   y   >>   5   )   +   d);
        y   -=  ( (   z   <<   4   )   +   a )  ^  ( z   +   sum  ) ^ (  (   z   >>   5   )   +   b);
        sum   -=   cnDelta;
    }
    (   (   unsigned   long   *   )aData   )[0]   =   y;
    (   (   unsigned   long   *   )aData   )[1]   =   z;
}

int SoftkeyYT88::sWriteEx(  DWORD in_data,DWORD *out_data,char *Path)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(WriteDword)(&in_data,Path);
    if(ret!=0)goto error1;
    ret=(ReadDword)(out_data,Path);
error1:
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::sWrite_2Ex(  DWORD in_data,DWORD *out_data,char *Path)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(WriteDword_2)(&in_data,Path);
    if(ret!=0)goto error1;
    ret=(ReadDword)(out_data,Path);
error1:
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::ReSet(char *InPath)
{

    int ret;int Version;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_GetVersion)(&Version,InPath);
    if(ret!=0)goto finish;
    ret=(NT_ReSet)(InPath);
    if(ret!=0)goto finish;
    ret=(NT_ReSet)(InPath);
    if(ret!=0)goto finish;
    ret=(NT_ReSet)(InPath);
    if(ret!=0)goto finish;
    ret=(NT_ReSet)(InPath);
finish:
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

 int SoftkeyYT88::NT_GetVersionEx(int *version,char *InPath )
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(F_GetVerEx)(version,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::SetCal_New(char *Key,char *InPath)
{
    BYTE KeyBuf[16];
    memset(KeyBuf,0,16);
    HexStringToByteArrayEx(Key,KeyBuf);
    //注意，这里是地址互换的
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_SetCal_New)(&KeyBuf[8],0,InPath);
    if(ret!=0)goto error1;
    ret=(NT_SetCal_New)(&KeyBuf[0],1,InPath);
error1:
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

int SoftkeyYT88::Cal_New(  BYTE *InBuf,BYTE *OutBuf,char *Path)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=NT_Cal_New(InBuf,OutBuf,Path);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::EncString_New(  char *InString,char *OutString,char *Path)
{

    int ret;int n;BYTE *outbuf;
    int len=lstrlenA(InString)+1;if(len<8)len=8;
    outbuf=new BYTE[len];
    memset(outbuf,0,len);
    memcpy(outbuf,InString,lstrlenA(InString)+1);
    for(n=0;n<=(len-8);n=n+8)
    {
        ret=Cal_New((BYTE *)&outbuf[n],&outbuf[n],Path);
        if(ret!=0){delete [] outbuf;return ret;}
    }
    ByteArrayToHexString(outbuf,OutString,len);
    delete [] outbuf;
    return ret;
}

void SoftkeyYT88::SwitchByte2Char(char *outstring,BYTE *inbyte,int inlen)
{
   int n;char temp[3];
   memset(outstring,0,ECC_MAXLEN*2);
   for(n=0;n<inlen;n++)
   {
        wsprintfA(temp,"%02X",inbyte[n]);
        lstrcatA(outstring,temp);
   }

}

void SoftkeyYT88::SwitchChar2Byte(char *instring,BYTE *outbyte)
{
   int n;char temp[3];
   int inlen=lstrlenA(instring)/2;
   for(n=0;n<inlen;n++)
   {
       temp[2]=(char)0;
       lstrcpynA(temp,&instring[n*2],2+1);
        *outbyte=HexToInt(temp);
        outbyte++;
   }

}

int SoftkeyYT88::YT_GenKeyPair(char* PriKey,char *PubKeyX,char *PubKeyY,char *InPath)
{

    int ret;BYTE b_PriKey[ECC_MAXLEN],b_PubKey[ECC_MAXLEN*2+1];//其中第一个字节是标志位，忽略
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_GenKeyPair)(b_PriKey,b_PubKey,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    memset(PriKey,0,2*ECC_MAXLEN+1);
    memset(PubKeyX,0,2*ECC_MAXLEN+1);
    memset(PubKeyY,0,2*ECC_MAXLEN+1);
    SwitchByte2Char(PriKey,b_PriKey,ECC_MAXLEN);
    SwitchByte2Char(PubKeyX,&b_PubKey[1],ECC_MAXLEN);
    SwitchByte2Char(PubKeyY,&b_PubKey[1+ECC_MAXLEN],ECC_MAXLEN);
    return ret;

}

int SoftkeyYT88::Set_SM2_KeyPair(char *PriKey,char *PubKeyX,char *PubKeyY,char *sm2UserName,char *InPath )
{

    int ret;BYTE b_PriKey[ECC_MAXLEN],b_PubKeyX[ECC_MAXLEN],b_PubKeyY[ECC_MAXLEN];
    SwitchChar2Byte(PriKey,b_PriKey);
    SwitchChar2Byte(PubKeyX,b_PubKeyX);
    SwitchChar2Byte(PubKeyY,b_PubKeyY);
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_Set_SM2_KeyPair)(b_PriKey,b_PubKeyX,b_PubKeyY,sm2UserName,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

int SoftkeyYT88::Get_SM2_PubKey(char *PubKeyX,char *PubKeyY,char *sm2UserName,char *InPath)
{

    int ret;BYTE b_PubKeyX[ECC_MAXLEN],b_PubKeyY[ECC_MAXLEN];
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_Get_SM2_PubKey)(b_PubKeyX,b_PubKeyY,sm2UserName,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    memset(PubKeyX,0,2*ECC_MAXLEN+1);
    memset(PubKeyY,0,2*ECC_MAXLEN+1);
    SwitchByte2Char(PubKeyX,b_PubKeyX,ECC_MAXLEN);
    SwitchByte2Char(PubKeyY,b_PubKeyY,ECC_MAXLEN);
    return ret;

}

int SoftkeyYT88::SM2_EncBuf(BYTE *InBuf,BYTE *OutBuf,int inlen,char *InPath)
{

    int ret,temp_inlen;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    while(inlen>0)
    {
        if(inlen>MAX_ENCLEN)
            temp_inlen=MAX_ENCLEN;
        else
            temp_inlen=inlen;
        ret=(NT_SM2_Enc)(InBuf,OutBuf,temp_inlen,InPath);
        if(ret!=0)goto err;
        inlen=inlen-MAX_ENCLEN;
        InBuf=InBuf+MAX_ENCLEN;
        OutBuf=OutBuf+MAX_DECLEN;
    }
err:
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

int SoftkeyYT88::SM2_DecBuf(BYTE *InBuf,BYTE *OutBuf,int inlen,char* pin,char *InPath)
{

    int ret,temp_inlen;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    while(inlen>0)
    {
        if(inlen>MAX_DECLEN)
            temp_inlen=MAX_DECLEN;
        else
            temp_inlen=inlen;
        ret=(NT_SM2_Dec)(InBuf,OutBuf,temp_inlen,pin,InPath);
        if(ret!=0)goto err;
        inlen=inlen-MAX_DECLEN;
        InBuf=InBuf+MAX_DECLEN;
        OutBuf=OutBuf+MAX_ENCLEN;
    }
err:
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

int SoftkeyYT88::SM2_EncString(char *InString,char *OutString,char *InPath)
{

    int inlen=lstrlenA(InString)+1;
    int outlen = (int)ceil((inlen*1.0 /MAX_ENCLEN)) * SM2_ADDBYTE+inlen;
    BYTE *OutBuf=new BYTE[outlen];
    BYTE *p=OutBuf;
    int ret,temp_inlen;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    while(inlen>0)
    {
        if(inlen>MAX_ENCLEN)
            temp_inlen=MAX_ENCLEN;
        else
            temp_inlen=inlen;
        ret=(NT_SM2_Enc)((BYTE *)InString,OutBuf,temp_inlen,InPath);
        if(ret!=0)goto err;
        inlen=inlen-MAX_ENCLEN;
        InString=InString+MAX_ENCLEN;
        OutBuf=OutBuf+MAX_DECLEN;
    }
err:
    memset(OutString,0,2*outlen+1);
    ByteArrayToHexString(p,OutString,outlen);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    delete [] p;
    return ret;

}

int SoftkeyYT88::SM2_DecString(char *InString,char *OutString,char* pin,char *InPath)
{

    int inlen=lstrlenA(InString)/2;
    BYTE *InByte=new BYTE[inlen];
    BYTE *p=InByte;
    int ret,temp_inlen;
    SwitchChar2Byte(InString,InByte);
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    while(inlen>0)
    {
        if(inlen>MAX_DECLEN)
            temp_inlen=MAX_DECLEN;
        else
            temp_inlen=inlen;
        ret=(NT_SM2_Dec)((BYTE *)InByte,(BYTE *)OutString,temp_inlen,pin,InPath);
        if(ret!=0)goto err;
        inlen=inlen-MAX_DECLEN;
        InByte=InByte+MAX_DECLEN;
        OutString=OutString+MAX_ENCLEN;
    }
err:
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    delete [] p;
    return ret;

}

int SoftkeyYT88::YtSetPin(char *old_pin,char *new_pin,char *InPath )
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_Set_Pin)(old_pin,new_pin,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

void SoftkeyYT88::SwitchBigInteger2Byte(char *instring,BYTE *outbyte,int *outlen)
{
    int n;char temp[3];
    int inlen=lstrlenA(instring)/2;
    *outlen=0x20;

    for(n=0;n<inlen;n++)
    {
        temp[2]=(char)0;
        lstrcpynA(temp,&instring[n*2],2+1);
        *outbyte=(BYTE)HexToInt(temp);
        outbyte++;
    }

}


int SoftkeyYT88::GetChipID( char *OutChipID,char *InPath)
{
    int ret;BYTE b_OutChipID[16];
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_GetChipID)(b_OutChipID,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    memset(OutChipID,0,33);
    ByteArrayToHexString(b_OutChipID,OutChipID,16);
    return ret;
}

int SoftkeyYT88::SetHidOnly(  BOOL IsHidOnly,char *InPath)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=NT_SetHidOnly(IsHidOnly,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}
int SoftkeyYT88::SetUReadOnly( char *InPath)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=NT_SetUReadOnly(InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::ReadVerfData(char *InPath)
{
    BYTE dataBuffer[50];HANDLE fileHandle;
    SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER sptdwb;
    ULONG length = 0,returned = 0;
    BOOL status = 0;
    char DevicePath[20];
    lstrcpyA(DevicePath,"\\\\.\\");lstrcatA(DevicePath,InPath);
    fileHandle = CreateFileA(DevicePath,GENERIC_WRITE | GENERIC_READ,FILE_SHARE_READ | FILE_SHARE_WRITE,NULL,OPEN_EXISTING, 0, NULL);
    if (fileHandle == INVALID_HANDLE_VALUE)return OPENUSBFAIL;
    ZeroMemory(&sptdwb, sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER));
    ZeroMemory(dataBuffer, DISK_INF_LEN);
    sptdwb.sptd.Length = sizeof(SCSI_PASS_THROUGH_DIRECT);
    sptdwb.sptd.PathId = 0;
    sptdwb.sptd.TargetId = 1;
    sptdwb.sptd.Lun = 0;
    sptdwb.sptd.CdbLength = 6;
    sptdwb.sptd.DataIn = SCSI_IOCTL_DATA_IN;
    sptdwb.sptd.SenseInfoLength = 24;
    sptdwb.sptd.DataTransferLength = DISK_INF_LEN;
    sptdwb.sptd.TimeOutValue = 100;
    sptdwb.sptd.DataBuffer = dataBuffer;
    sptdwb.sptd.SenseInfoOffset =
        offsetof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER,ucSenseBuf);
    sptdwb.sptd.Cdb[0] = 0x12;
    sptdwb.sptd.Cdb[4] = DISK_INF_LEN;                         // 命令
    length = sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER);

    status = DeviceIoControl(fileHandle,
        IOCTL_SCSI_PASS_THROUGH_DIRECT,
        &sptdwb,
        length,
        &sptdwb,
        length,
        &returned,
        FALSE);

    CloseHandle(fileHandle);
    if((sptdwb.sptd.ScsiStatus == 0) && (status != 0) )
    {
        if(memcmp(dataBuffer,DISK_INF,DISK_INF_LEN)==0)
        {
            //MessageBox(NULL,DevicePath,"OK",MB_OK);
            return 0;
        }
    }
    return OPENUSBFAIL;
}

int SoftkeyYT88::sFindPort(short pos,char *OutPath)
{
    DWORD   dwBuffer=512*2;   char cdriver[10]="";int  nSize;int len=1;//char temp[30]="";
    char   szBuffer[512*2];
    int count=0;
    DWORD lpSectorsPerCluster;
    DWORD lpBytesPerSector;
    DWORD lpNumberOfFreeClusters;
    DWORD lpTotalNumberOfClusters;
    UINT   nPreErrorMode;

    //ADD 2008-4-5
    ZeroMemory(OutPath,sizeof(OutPath));
    {
        //return isfindmydevice(pos,OutPath,count);
        ZeroMemory(   szBuffer,    dwBuffer   );
        nSize   =   GetLogicalDriveStringsA(   dwBuffer,   szBuffer   );
        while(nSize>=4)
        {
            nSize=nSize-4;
            lstrcpyA(cdriver,&szBuffer[nSize]);
            len=lstrlenA(cdriver);
            cdriver[len-1]=0;
            if((cdriver[0]=='a') || (cdriver[0]=='A') || (cdriver[0]=='b') || (cdriver[0]=='B'))continue;
            if((GetDriveTypeA(cdriver)==DRIVE_CDROM) || (GetDriveTypeA(cdriver)==DRIVE_REMOTE) ||
                (GetDriveTypeA(cdriver)==DRIVE_UNKNOWN))continue;
            //#ifdef _CHECKDISK
            /*add-2010-6-13是否需要这个，注意如果容量改变，这个要改变	*/
            nPreErrorMode   =   ::SetErrorMode(SEM_FAILCRITICALERRORS)   ;
            GetDiskFreeSpaceA(cdriver,&lpSectorsPerCluster,&lpBytesPerSector,&lpNumberOfFreeClusters,&lpTotalNumberOfClusters);
            SetErrorMode(nPreErrorMode) ;
            if(lpTotalNumberOfClusters!=344|| lpSectorsPerCluster!=1 )continue;

            //#endif
            if(ReadVerfData(cdriver)==0)
            {

                if(pos==count)
                {
                    lstrcpyA(OutPath,"\\\\.\\");
                    lstrcatA(OutPath,cdriver);
                    return 0;

                }
                (count)++;
            }
        }
    }
    return NOUSBKEY;
}

int SoftkeyYT88::FindU(int pos,char *OutPath)
{
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    int ret=sFindPort(pos,OutPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int  SoftkeyYT88::NT_FindU_2(  int start,DWORD in_data,DWORD verf_data,char*OutPath )
{
    int pos;DWORD out_data;int ret;
    for(pos=start;pos<127;pos++)
    {
        if(sFindPort(pos,OutPath)!=0){return -92;}
        ret=WriteDword( &in_data,OutPath);
        if(ret!=0){return ret;}
        ret=ReadDword( &out_data,OutPath);
        if(ret!=0){return ret;}
        if(out_data==verf_data){return 0;}
    }
    ZeroMemory(OutPath,sizeof(OutPath));
    return -92;
}

int SoftkeyYT88::FindU_2(  int start,DWORD in_data,DWORD verf_data,char*OutPath)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_FindU_2)(start,in_data,verf_data,OutPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

int SoftkeyYT88::NT_IsUReadOnly(BOOL *IsReadOnly,char *InPath)
{
    BYTE dataBuffer[50];HANDLE fileHandle;
    SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER sptdwb;
    ULONG length = 0,returned = 0;
    BOOL status = 0;
    char DevicePath[20];
    lstrcpyA(DevicePath,"\\\\.\\");lstrcatA(DevicePath,InPath);
    fileHandle = CreateFileA(DevicePath,GENERIC_WRITE | GENERIC_READ,FILE_SHARE_READ | FILE_SHARE_WRITE,NULL,OPEN_EXISTING, 0, NULL);
    if (fileHandle == INVALID_HANDLE_VALUE)return OPENUSBFAIL;
    ZeroMemory(&sptdwb, sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER));
    ZeroMemory(dataBuffer, DISK_SENSE_LEN);
    sptdwb.sptd.Length = sizeof(SCSI_PASS_THROUGH_DIRECT);
    sptdwb.sptd.PathId = 0;
    sptdwb.sptd.TargetId = 1;
    sptdwb.sptd.Lun = 0;
    sptdwb.sptd.CdbLength = 6;
    sptdwb.sptd.DataIn = SCSI_IOCTL_DATA_IN;
    sptdwb.sptd.SenseInfoLength = 24;
    sptdwb.sptd.DataTransferLength = DISK_SENSE_LEN;
    sptdwb.sptd.TimeOutValue = 100;
    sptdwb.sptd.DataBuffer = dataBuffer;
    sptdwb.sptd.SenseInfoOffset =
        offsetof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER,ucSenseBuf);
    sptdwb.sptd.Cdb[0] = 0x1a;
    sptdwb.sptd.Cdb[2] = SCSI_MSPGCD_RETALL;
    sptdwb.sptd.Cdb[4] = DISK_SENSE_LEN;                         // 命令
    length = sizeof(SCSI_PASS_THROUGH_DIRECT_WITH_BUFFER);

    status = DeviceIoControl(fileHandle,
        IOCTL_SCSI_PASS_THROUGH_DIRECT,
        &sptdwb,
        length,
        &sptdwb,
        length,
        &returned,
        FALSE);

    CloseHandle(fileHandle);
    if((sptdwb.sptd.ScsiStatus == 0) && (status != 0) )
    {
        if(dataBuffer[2]==0x80)
        {
            *IsReadOnly=TRUE;
        }
        else
            *IsReadOnly=FALSE;
        return 0;
    }
    return OPENUSBFAIL;
}

int SoftkeyYT88::IsUReadOnly(BOOL *IsReadOnly,char *InPath)
{
    int ret;
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=NT_IsUReadOnly(IsReadOnly,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;
}

void SoftkeyYT88::EnCode(   BYTE  * InData,BYTE  * OutData,  char *Key  )
{
    BYTE KeyBuf[16];
    memset(KeyBuf,0,16);
    HexStringToByteArrayEx(Key,KeyBuf);
    memcpy(OutData,InData,8);
    EncBySoft(OutData,KeyBuf);
}

void SoftkeyYT88::DeCode(   BYTE  * InData, BYTE  * OutData, char *Key  )
{
    BYTE KeyBuf[16];
    memset(KeyBuf,0,16);
    HexStringToByteArrayEx(Key,KeyBuf);
    memcpy(OutData,InData,8);
    DecBySoft(OutData,KeyBuf);
}

void SoftkeyYT88::StrDec(  char *InString,char *OutString,char *Key)
{
  int n;
  int len=lstrlenA(InString)/2;
  BYTE KeyBuf[16];
  memset(KeyBuf,0,16);
  HexStringToByteArrayEx(Key,KeyBuf);
  HexStringToByteArray(InString,(BYTE *)OutString);
  for(n=0;n<=(len-8);n=n+8)
    {
      DecBySoft((BYTE *)&OutString[n],KeyBuf);
    }
  return ;
}

void SoftkeyYT88::StrEnc(  char *InString,char *OutString,char *Key)
{
  int n;BYTE *outbuf;
  int len=lstrlenA(InString)+1;if(len<8)len=8;
  BYTE KeyBuf[16];
  memset(KeyBuf,0,16);
  HexStringToByteArrayEx(Key,KeyBuf);
  outbuf=new BYTE[len];
  memset(outbuf,0,len);
  memcpy(outbuf,InString,lstrlenA(InString)+1);
  for(n=0;n<=(len-8);n=n+8)
    {
      EncBySoft(&outbuf[n],KeyBuf);
    }
  ByteArrayToHexString(outbuf,OutString,len);
  delete [] outbuf;
}

int SoftkeyYT88::GetProduceDate(  char *OutDate,char *InPath)
{
    int ret;
    BYTE B_OutBDate[8];
    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=(NT_GetProduceDate)(B_OutBDate,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    ByteArrayToHexString(B_OutBDate,OutDate, 8);
    return ret;
}

int SoftkeyYT88::SetID(char * Seed,char *InPath)
{

    int ret;
    BYTE KeyBuf[8];
    memset(KeyBuf,0,8);
    HexStringToByteArray(Seed,KeyBuf);

    HANDLE hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");
    WaitForSingleObject(hsignal,INFINITE);
    ret=NT_SetID(KeyBuf,InPath);
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

int SoftkeyYT88::Y_SetCal(BYTE *InData,short address,short len,BYTE *password,char *Path )
{
       short addr_l,addr_h;int n;int ret;
   BYTE array_in[25],array_out[25];
   HANDLE hUsbDevice=MyOpenPath(Path);
    if(hUsbDevice == INVALID_HANDLE_VALUE)return NOUSBKEY;

   if(len>8)return -87;
   if(address+len-1>2047 || address<0)return ErrAddrOver;
   {addr_h=(address>>8)<<1;addr_l=address&0xff;}

   array_in[1]=SETCAL;//read 0x10;write 0x11;
   array_in[2]=(BYTE)addr_h;//0x01;//read 0x80 ;write 0x40;
   array_in[3]=(BYTE)addr_l;
   array_in[4]=(BYTE )len;
   for(n=0;n<8;n++)
   {
       array_in[5+n]=*password;
       password++;
   }
   for(n=0;n<len;n++)
   {
       array_in[13+n]=*InData;
       InData++;
   }
   ret= Hanldetransfe(hUsbDevice,array_in,13+len,array_out,1,Path);
   if(ret!=0)return ret;

   if(array_out[0]!=0x0)
   {
       return ErrWritePWD;//表示写失败；
   }
   return 0;
}


int  SoftkeyYT88::SetCal(char * W_HKey,char *W_LKey,char * new_HKey,char *new_LKey,char *InPath)
{

    BYTE ary1[8];BYTE ary2[8];	int ret;short address=0x7f0-8;

    myconvert(W_HKey,W_LKey,ary1);
    myconvert(new_HKey,new_LKey,ary2);

    HANDLE	hsignal=CreateSemaphoreA(NULL,1,1,"ex_sim");

    WaitForSingleObject(hsignal,INFINITE);
    ret=Y_SetCal(ary2,address,8,ary1,InPath);
    if(ret!=0){ReleaseSemaphore(hsignal,1,NULL);return ret;}
    ReleaseSemaphore(hsignal,1,NULL);
    CloseHandle(hsignal);
    return ret;

}

void  SoftkeyYT88::SnToProduceDate(char* InSn,char *OutProduceDate)
{

   char temp[5]="";
   memset(temp,0,5);
   lstrcpynA(temp,&InSn[0],2+1);
   int year=2000 + HexToInt(temp);
   lstrcpynA(temp,&InSn[2],2+1);
   int month=  HexToInt(temp);
   lstrcpynA(temp,&InSn[4],2+1);
   int day=  HexToInt(temp);
   lstrcpynA(temp,&InSn[6],2+1);
   int hour=  HexToInt(temp);
   lstrcpynA(temp,&InSn[8],2+1);
   int minutes=  HexToInt(temp);
   lstrcpynA(temp,&InSn[10],2+1);
   int sec=  HexToInt(temp);
   lstrcpynA(temp,&InSn[12],4+1);
   int sn=  HexToInt(temp);
    wsprintfA(OutProduceDate,"%d年%d月%d日%d时%d分%d秒--序号：%d", year,month,day,hour,minutes,sec,sn);
}
