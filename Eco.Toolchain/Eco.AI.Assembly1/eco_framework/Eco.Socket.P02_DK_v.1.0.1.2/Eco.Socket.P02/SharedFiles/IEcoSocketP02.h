/*
 * <кодировка символов>
 *   Cyrillic (UTF-8 with signature) - Codepage 65001
 * </кодировка символов>
 *
 * <сводка>
 *   IEcoSocketP02
 * </сводка>
 *
 * <описание>
 *   Данный заголовок описывает реализацию интерфейсов функций API заголовочного файла <sys/socket.h>,
 *   согластно спецификации POSIX.1 для UNIX подобных ОС.
 * </описание>
 *
 * <ссылка>
 *   Спецификация: Information technology — Portable Operating System Interface (POSIX ® ) — Part 1: Base Definitions
 *                 ISO/IEC 9945-1:2002
 *                 https://www.iso.org/standard/37312.html
 * </ссылка>
 *
 * <автор>
 *   Copyright (c) 2018 Vladimir Bashev. All rights reserved.
 * </автор>
 *
 */

#ifndef __I_ECO_SOCKET_POSIX_2002_H__
#define __I_ECO_SOCKET_POSIX_2002_H__

#include "IEcoBase1.h"

/*
 * Types
 */
#ifndef ECO_SOCK_MACROS_DEFINED
#define SOCK_STREAM     1       /* stream socket */
#define SOCK_DGRAM      2       /* datagram socket */
#define SOCK_RAW        3       /* raw-protocol interface */
#define SOCK_RDM        4       /* reliably-delivered message */
#define SOCK_SEQPACKET  5       /* sequenced packet stream */
#define SOCK_NONBLOCK   0x4000  /* set O_NONBLOCK */
#define ECO_SOCK_MACROS_DEFINED
#endif

/*
 * Option flags.
 */
#ifndef ECO_SO_MACROS_DEFINED
#define SO_DEBUG        0x0001  /* debugging information is being recorded. */
#define SO_ACCEPTCONN   0x0002  /* socket is accepting connections. */
#define SO_REUSEADDR    0x0004  /* reuse oflocal addresses is supported. */
#define SO_KEEPALIVE    0x0008  /* connections are kept alive with periodic messages. */
#define SO_DONTROUTE    0x0010  /* bypass normal routing. */
#define SO_BROADCAST    0x0020  /* transmission ofbroadcast messages is supported. */
#define SO_USELOOPBACK  0x0040  /* bypass hardware when possible */
#define SO_LINGER       0x0080  /* socket lingers on close. */
#define SO_OOBINLINE    0x0100  /* out-of-band data is transmitted in line. */
#define SO_REUSEPORT    0x0200  /* allow local address & port reuse */
#define SO_TIMESTAMP    0x0800  /* timestamp received dgram traffic */
#define SO_BINDANY      0x1000  /* allow bind to any address */
#define SO_SNDBUF       0x1001  /* send buffer size. */
#define SO_RCVBUF       0x1002  /* receive buffer size */
#define SO_SNDLOWAT     0x1003  /* send low-water mark */
#define SO_RCVLOWAT     0x1004  /* receive low-water mark */
#define SO_SNDTIMEO     0x1005  /* send timeout */
#define SO_RCVTIMEO     0x1006  /* receive timeout */
#define SO_ERROR        0x1007  /* get error status and clear */
#define SO_TYPE         0x1008  /* get socket type */
#define SO_NETPROC      0x1020  /* multiplex; network processing */
#define SO_RTABLE       0x1021  /* routing table to be used */
#define SO_PEERCRED     0x1022  /* get connect-time credentials */
#define SO_SPLICE       0x1023  /* splice data to other socket */
#define SO_DOMAIN       0x1024  /* get socket domain */
#define SO_PROTOCOL     0x1025  /* get socket protocol */
#define SO_ZEROIZE      0x2000  /* zero out all mbufs sent over socket */
#define ECO_SO_MACROS_DEFINED
#endif

/*
 * Level number for (get/set)sockopt() to apply to socket itself.
 */
#ifndef ECO_SOL_MACROS_DEFINED
#define SOL_SOCKET  0xffff  /* options for socket level */
#define ECO_SOL_MACROS_DEFINED
#endif

/*
 * Address families.
 */
#ifndef ECO_AF_MACROS_DEFINED
#define AF_UNSPEC       0       /* unspecified */
#define AF_UNIX         1       /* local to host */
#define AF_LOCAL        AF_UNIX /* draft POSIX compatibility */
#define AF_INET         2       /* internetwork: UDP, TCP, etc. */
#define AF_IMPLINK      3       /* arpanet imp addresses */
#define AF_PUP          4       /* pup protocols: e.g. BSP */
#define AF_CHAOS        5       /* mit CHAOS protocols */
#define AF_NS           6       /* XEROX NS protocols */
#define AF_ISO          7       /* ISO protocols */
#define AF_OSI          AF_ISO
#define AF_ECMA         8       /* european computer manufacturers */
#define AF_DATAKIT      9       /* datakit protocols */
#define AF_CCITT        10      /* CCITT protocols, X.25 etc */
#define AF_SNA          11      /* IBM SNA */
#define AF_DECnet       12      /* DECnet */
#define AF_DLI          13      /* DEC Direct data link interface */
#define AF_LAT          14      /* LAT */
#define AF_HYLINK       15      /* NSC Hyperchannel */
#define AF_APPLETALK    16      /* Apple Talk */
#define AF_ROUTE        17      /* Internal Routing Protocol */
#define AF_LINK         18      /* Link layer interface */
#define pseudo_AF_XTP	19      /* eXpress Transfer Protocol (no AF) */
#define AF_COIP         20      /* connection-oriented IP, aka ST II */
#define AF_CNT          21      /* Computer Network Technology */
#define pseudo_AF_RTIP  22      /* Help Identify RTIP packets */
#define AF_IPX          23      /* Novell Internet Protocol */
#define AF_INET6        24      /* IPv6 */
#define pseudo_AF_PIP   25      /* Help Identify PIP packets */
#define AF_ISDN         26      /* Integrated Services Digital Network*/
#define AF_E164         AF_ISDN /* CCITT E.164 recommendation */
#define AF_NATM         27      /* native ATM access */
#define AF_ENCAP        28
#define AF_SIP          29      /* Simple Internet Protocol */
#define AF_KEY          30
#define pseudo_AF_HDRCMPLT 31   /* Used by BPF to not rewrite headers in interface output routine */
#define AF_BLUETOOTH    32      /* Bluetooth */
#define AF_MPLS         33      /* MPLS */
#define pseudo_AF_PFLOW 34      /* pflow */
#define pseudo_AF_PIPEX 35      /* PIPEX */
#define AF_MAX          36
#define ECO_AF_MACROS_DEFINED
#endif

/*
 * Protocol families, same as address families for now.
 */
#ifndef ECO_PF_MACROS_DEFINED
#define PF_UNSPEC       AF_UNSPEC
#define PF_LOCAL        AF_LOCAL
#define PF_UNIX         AF_UNIX
#define PF_INET         AF_INET
#define PF_IMPLINK      AF_IMPLINK
#define PF_PUP          AF_PUP
#define PF_CHAOS        AF_CHAOS
#define PF_NS           AF_NS
#define PF_ISO          AF_ISO
#define PF_OSI          AF_ISO
#define PF_ECMA         AF_ECMA
#define PF_DATAKIT      AF_DATAKIT
#define PF_CCITT        AF_CCITT
#define PF_SNA          AF_SNA
#define PF_DECnet       AF_DECnet
#define PF_DLI          AF_DLI
#define PF_LAT          AF_LAT
#define PF_HYLINK       AF_HYLINK
#define PF_APPLETALK    AF_APPLETALK
#define PF_ROUTE        AF_ROUTE
#define PF_LINK         AF_LINK
#define PF_XTP          pseudo_AF_XTP
#define PF_COIP         AF_COIP
#define PF_CNT          AF_CNT
#define PF_IPX          AF_IPX
#define PF_INET6        AF_INET6
#define PF_RTIP         pseudo_AF_RTIP
#define PF_PIP          pseudo_AF_PIP
#define PF_ISDN         AF_ISDN
#define PF_NATM         AF_NATM
#define PF_ENCAP        AF_ENCAP
#define PF_SIP          AF_SIP
#define PF_KEY          AF_KEY
#define PF_BPF          pseudo_AF_HDRCMPLT
#define PF_BLUETOOTH    AF_BLUETOOTH
#define PF_MPLS         AF_MPLS
#define PF_PFLOW        pseudo_AF_PFLOW
#define PF_PIPEX        pseudo_AF_PIPEX
#define PF_MAX          AF_MAX
#define ECO_PF_MACROS_DEFINED
#endif

/*
 * These are the valid values for the "how" field used by shutdown(2).
 */
#ifndef ECO_MSG_MACROS_DEFINED
#define MSG_OOB             0x1     /* process out-of-band data */
#define MSG_PEEK            0x2     /* peek at incoming message */
#define MSG_DONTROUTE       0x4     /* send without using routing tables */
#define MSG_EOR             0x8     /* data completes record */
#define MSG_TRUNC           0x10    /* data discarded before delivery */
#define MSG_CTRUNC          0x20    /* control data lost before delivery */
#define MSG_WAITALL         0x40    /* wait for full request or error */
#define MSG_DONTWAIT        0x80    /* this message should be nonblocking */
#define MSG_BCAST           0x100   /* this message rec'd as broadcast */
#define MSG_MCAST           0x200   /* this message rec'd as multicast */
#define MSG_NOSIGNAL        0x400   /* do not send SIGPIPE */
#define MSG_CMSG_CLOEXEC    0x800   /* set FD_CLOEXEC on received fds */
#define MSG_WAITFORONE      0x1000  /* nonblocking but wait for one msg */
#define ECO_MSG_MACROS_DEFINED
#endif

#ifndef ECO_IPPROTO_MACROS_DEFINED
#define IPPROTO_IP              0               /* Internet protocol */
#define IPPROTO_ICMP            1               /* Control message protocol */
#define IPPROTO_IGMP            2               /* Group management protocol */
#define IPPROTO_TCP             6               /* Transmission control protocol. */
#define IPPROTO_UDP             17              /* User datagram protocol. */
#define IPPROTO_RAW             255             /* Raw IP Packets Protocol. */
#define IPPROTO_MAX             256
#define ECO_IPPROTO_MACROS_DEFINED
#endif

#ifndef ECO_INADDR_MACROS_DEFINED
#define INADDR_ANY              0x00000000      /* IPv4 local host address. */
#define INADDR_LOOPBACK         0x7f000001      /* IPv4 loopback address. */
#define INADDR_BROADCAST        0xffffffff      /* IPv4 broadcast address. */
#define INADDR_NONE             0xffffffff      /* None */
#define ECO_INADDR_MACROS_DEFINED
#endif

/*
 * These are the valid values for the "how" field used by shutdown(2).
 */
#ifndef ECO_SHUT_MACROS_DEFINED
#define SHUT_RD     0
#define SHUT_WR     1
#define SHUT_RDWR   2
#define ECO_SHUT_MACROS_DEFINED
#endif

#ifndef ECO_SOCKLEN_T_DEFINED
typedef int socklen_t;
#define ECO_SOCKLEN_T_DEFINED
#endif

#ifndef ECO_SSIZE_T_DEFINED
typedef int ssize_t;
#define ECO_SSIZE_T_DEFINED
#endif

#ifndef ECO_SA_FAMILY_T_DEFINED
typedef int sa_family_t;
#define ECO_SA_FAMILY_T_DEFINED
#endif

#ifndef ECO_SOCKADDR_DEFINED
struct sockaddr {
    uint8_t     sa_len;         /* total length */
    sa_family_t sa_family;      /* address family */
    char        sa_data[14];    /* actually longer; address value */
};
#define ECO_SOCKADDR_DEFINED
#endif

#ifndef ECO_IN_ADDR_T_DEFINED
typedef uint32_t      in_addr_t;    /* base type for internet address */
#define ECO_IN_ADDR_T_DEFINED
#endif
#ifndef ECO_IN_PORT_T_DEFINED
typedef uint16_t      in_port_t;    /* IP port type */
#define ECO_IN_PORT_T_DEFINED
#endif

#ifndef ECO_IN_ADDR_DEFINED
struct in_addr {
    in_addr_t s_addr;
};
#define ECO_IN_ADDR_DEFINED
#endif

#ifndef ECO_SOCKADDR_IN_DEFINED
typedef struct sockaddr_in {
  short          sin_family;
  uint16_t       sin_port;
  struct in_addr sin_addr;
  char           sin_zero[8];
};
#define ECO_SOCKADDR_IN_DEFINED
#endif


/* <sys/uio.h> */
#ifndef ECO_IOVEC_DEFINED
struct iovec {
    void    *iov_base;  /* Base address. */
    size_t  iov_len;    /* Length. */
};
#define ECO_IOVEC_DEFINED
#endif

#ifndef ECO_MSGHDR_DEFINED
struct msghdr {
    void            *msg_name;      /* optional address */
    socklen_t       msg_namelen;    /* size of address */
    struct iovec    *msg_iov;       /* scatter/gather array */
    unsigned int    msg_iovlen;     /* # elements in msg_iov */
    void            *msg_control;   /* ancillary data, see below */
    socklen_t       msg_controllen; /* ancillary data buffer len */
    int             msg_flags;      /* flags on received message */
};
#define ECO_MSGHDR_DEFINED
#endif

#ifndef ECO_MMSGHDR_DEFINED
struct mmsghdr {
    struct msghdr msg_hdr;
    unsigned int msg_len;
};
#define ECO_MMSGHDR_DEFINED
#endif


/* IEcoINetP02 IID = {2C313FFA-19C2-4D63-82F0-62E83B1DC103} */
#ifndef __IID_IEcoINetP02
static const UGUID IID_IEcoINetP02 = {0x01, 0x10, {0x2C, 0x31, 0x3F, 0xFA, 0x19, 0xC2, 0x4D, 0x63, 0x82, 0xF0, 0x62, 0xE8, 0x3B, 0x1D, 0xC1, 0x03}};
#endif /* __IID_IEcoINetP02 */

typedef struct IEcoINetP02* IEcoINetP02Ptr_t;

typedef struct IEcoINetP02VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoINetP02Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoINetP02Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoINetP02Ptr_t me);

    /* IEcoINetP02 */
    uint32_t (ECOCALLMETHOD *htonl)(/* in */ IEcoINetP02Ptr_t me, uint32_t);
    uint16_t (ECOCALLMETHOD *htons)(/* in */ IEcoINetP02Ptr_t me, uint16_t);
    uint32_t (ECOCALLMETHOD *ntohl)(/* in */ IEcoINetP02Ptr_t me, uint32_t);
    uint16_t (ECOCALLMETHOD *ntohs)(/* in */ IEcoINetP02Ptr_t me, uint16_t);
    in_addr_t (ECOCALLMETHOD *inet_addr)(/* in */ IEcoINetP02Ptr_t me, const char *);
    char* (ECOCALLMETHOD *inet_ntoa)(/* in */ IEcoINetP02Ptr_t me, struct in_addr);
    const char* (ECOCALLMETHOD *inet_ntop)(/* in */ IEcoINetP02Ptr_t me, int, const void* /* restrict */, char* /* restrict */, socklen_t);
    int (ECOCALLMETHOD *inet_pton)(/* in */ IEcoINetP02Ptr_t me, int, const char* /* restrict */, void* /* restrict */);

} IEcoINetP02VTbl, *IEcoINetP02VTblPtr_t;

interface IEcoINetP02 {
    struct IEcoINetP02VTbl *pVTbl;
} IEcoINetP02;


/* IEcoSocketP02 IID = {8EDA7C36-A3D0-422A-9C10-189A2BB86F5F} */
#ifndef __IID_IEcoSocketP02
static const UGUID IID_IEcoSocketP02 = {0x01, 0x10, {0x8E, 0xDA, 0x7C, 0x36, 0xA3, 0xD0, 0x42, 0x2A, 0x9C, 0x10, 0x18, 0x9A, 0x2B, 0xB8, 0x6F, 0x5F}};
#endif /* __IID_IEcoSocketP02 */

typedef struct IEcoSocketP02* IEcoSocketP02Ptr_t;

typedef struct IEcoSocketP02VTbl {

    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* in */ IEcoSocketP02Ptr_t me, /* in */ const UGUID* riid, /* out */ voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(/* in */ IEcoSocketP02Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(/* in */ IEcoSocketP02Ptr_t me);

    /* IEcoSocketP02 */
    int (ECOCALLMETHOD *accept)(/* in */ IEcoSocketP02Ptr_t me, int, struct sockaddr *, socklen_t *);
    int (ECOCALLMETHOD *bind)(/* in */ IEcoSocketP02Ptr_t me, int, const struct sockaddr *, socklen_t);
    int (ECOCALLMETHOD *connect)(/* in */ IEcoSocketP02Ptr_t me, int, const struct sockaddr *, socklen_t);
    int (ECOCALLMETHOD *getpeername)(/* in */ IEcoSocketP02Ptr_t me, int, struct sockaddr *, socklen_t *);
    int (ECOCALLMETHOD *getsockname)(/* in */ IEcoSocketP02Ptr_t me, int, struct sockaddr *, socklen_t *);
    int (ECOCALLMETHOD *getsockopt)(/* in */ IEcoSocketP02Ptr_t me, int, int, int, void *, socklen_t *);
    int (ECOCALLMETHOD *listen)(/* in */ IEcoSocketP02Ptr_t me, int, int);
    ssize_t (ECOCALLMETHOD *recv)(/* in */ IEcoSocketP02Ptr_t me, int, void *, size_t, int);
    ssize_t (ECOCALLMETHOD *recvfrom)(/* in */ IEcoSocketP02Ptr_t me, int, void *, size_t, int, struct sockaddr *, socklen_t *);
    ssize_t (ECOCALLMETHOD *recvmsg)(/* in */ IEcoSocketP02Ptr_t me, int, struct msghdr *, int);
    int (ECOCALLMETHOD *recvmmsg)(/* in */ IEcoSocketP02Ptr_t me, int, struct mmsghdr *, unsigned int, int, struct timespec *);
    ssize_t (ECOCALLMETHOD *send)(/* in */ IEcoSocketP02Ptr_t me, int, const void *, size_t, int);
    ssize_t (ECOCALLMETHOD *sendto)(/* in */ IEcoSocketP02Ptr_t me, int, const void *, size_t, int, const struct sockaddr *, socklen_t);
    ssize_t (ECOCALLMETHOD *sendmsg)(/* in */ IEcoSocketP02Ptr_t me, int, const struct msghdr *, int);
    int (ECOCALLMETHOD *sendmmsg)(/* in */ IEcoSocketP02Ptr_t me, int, struct mmsghdr *, unsigned int, int);
    int (ECOCALLMETHOD *setsockopt)(/* in */ IEcoSocketP02Ptr_t me, int, int, int, const void *, socklen_t);
    int (ECOCALLMETHOD *shutdown)(/* in */ IEcoSocketP02Ptr_t me, int, int);
    int (ECOCALLMETHOD *sockatmark)(/* in */ IEcoSocketP02Ptr_t me, int);
    int (ECOCALLMETHOD *socket)(/* in */ IEcoSocketP02Ptr_t me, int, int, int);
    int (ECOCALLMETHOD *socketpair)(/* in */ IEcoSocketP02Ptr_t me, int, int, int, int *);

} IEcoSocketP02VTbl, *IEcoSocketP02VTblPtr_t;

interface IEcoSocketP02 {
    struct IEcoSocketP02VTbl *pVTbl;
} IEcoSocketP02;


#endif /* __I_ECO_SOCKET_POSIX_2002_H__ */
