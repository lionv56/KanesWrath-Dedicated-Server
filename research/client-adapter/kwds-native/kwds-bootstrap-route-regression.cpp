#include "kwds-bootstrap-route.h"
using namespace kwds_route;
static_assert(IsBootstrapDnsName("servserv.generals.ea.com"));
static_assert(IsBootstrapDnsName("SERVSERV.GENERALS.EA.COM"));
static_assert(!IsBootstrapDnsName(nullptr));
static_assert(!IsBootstrapDnsName("servserv.generals.ea.com.attacker.invalid"));
static_assert(!IsBootstrapDnsName("credentials.invalid"));
static_assert(IsBootstrapSocketTarget(0x7F000001u,80,true));
static_assert(!IsBootstrapSocketTarget(0x7F000001u,80,false));
static_assert(!IsBootstrapSocketTarget(0x7F000001u,0,true));
static_assert(!IsBootstrapSocketTarget(0x7F000002u,80,true));
static_assert(!IsBootstrapSocketTarget(0xC0000201u,80,true));
static_assert(IsBootstrapSocketTarget(0xC33CA63Du,80,false));
static_assert(IsBootstrapSocketTarget(0xC33CA63Du,80,true));
