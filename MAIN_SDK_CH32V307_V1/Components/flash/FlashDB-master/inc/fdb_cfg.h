#ifndef _FDB_CFG_H_
#define _FDB_CFG_H_

int flashdb_printf(const char *fmt, ...);

/* Use KVDB feature. */
#define FDB_USING_KVDB

/* Use TSDB feature (optional at runtime). */
#define FDB_USING_TSDB

/* Use FAL as storage backend. */
#define FDB_USING_FAL_MODE

#ifdef FDB_USING_FAL_MODE
/* NOR flash write granularity (bit): 1 means byte-writable NOR behavior. */
#define FDB_WRITE_GRAN 1
#endif

/* Keep log output enabled for bring-up and debugging. */
#define FDB_DEBUG_ENABLE

/* Route FlashDB log to CRLF-aware port print. */
#define FDB_PRINT(...) flashdb_printf(__VA_ARGS__)

#endif /* _FDB_CFG_H_ */
