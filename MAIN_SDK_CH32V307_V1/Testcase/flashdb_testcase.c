/**
 * @file flashdb_testcase.c
 * @brief FlashDB basic testcase with SFUD-backed FAL storage.
 */

#include "sdkconfig.h"
#include "flashdb.h"
#include "shell.h"

#ifdef log_e
#undef log_e
#endif
#ifdef log_i
#undef log_i
#endif
#ifdef log_d
#undef log_d
#endif

#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/flashdb/"

#if defined(SDK_USING_TESTCASE_W25Q16)

static struct fdb_default_kv_node default_kv_table[] = {
    {"username", "ch32v307"},
    {"version", "1.0.0"},
};

static struct fdb_kvdb kvdb = {0};
static uint8_t kvdb_inited = 0;

static int fdb_kvdb_ensure_init(void)
{
    fdb_err_t result;
    struct fdb_default_kv default_kv;

    if (kvdb_inited) {
        return 0;
    }

    default_kv.kvs = default_kv_table;
    default_kv.num = sizeof(default_kv_table) / sizeof(default_kv_table[0]);

    result = fdb_kvdb_init(&kvdb, "env", "fdb_kvdb1", &default_kv, NULL);
    if (result != FDB_NO_ERR) {
        log_e("fdb_kvdb_init failed, err=%d.", (int)result);
        return -1;
    }

    kvdb_inited = 1;
    return 0;
}

/**
 * @brief FlashDB KVDB quick self-check.
 * @param mode Example selector.
 * @return 0 on success, -1 on failure.
 */
int case_fdb(int mode)
{
    if (fdb_kvdb_ensure_init() != 0) {
        return -1;
    }

    switch (mode) {
    case 1: {
        fdb_err_t result;
        const char *read_back;

        result = fdb_kv_set(&kvdb, "hello", "flashdb+sfud");
        if (result != FDB_NO_ERR) {
            log_e("mode1: fdb_kv_set failed, err=%d.", (int)result);
            return -1;
        }

        read_back = fdb_kv_get(&kvdb, "hello");
        if (read_back == NULL) {
            log_e("mode1: fdb_kv_get failed.");
            return -1;
        }

        log_i("mode1: hello=%s", read_back);
        return 0;
    }

    case 2: {
        fdb_err_t result;
        struct fdb_blob blob;
        uint32_t w = 12345678;
        uint32_t r = 0;
        size_t read_len;

        result = fdb_kv_set_blob(&kvdb, "count_blob", fdb_blob_make(&blob, &w, sizeof(w)));
        if (result != FDB_NO_ERR) {
            log_e("mode2: fdb_kv_set_blob failed, err=%d.", (int)result);
            return -1;
        }

        read_len = fdb_kv_get_blob(&kvdb, "count_blob", fdb_blob_make(&blob, &r, sizeof(r)));
        if (read_len != sizeof(r)) {
            log_e("mode2: fdb_kv_get_blob failed, len=%d.", (int)read_len);
            return -1;
        }

        log_i("mode2: count_blob=%lu", (unsigned long)r);
        return 0;
    }

    case 3: {
        fdb_err_t result;

        result = fdb_kv_del(&kvdb, "hello");
        if (result != FDB_NO_ERR) {
            log_e("mode3: fdb_kv_del failed, err=%d.", (int)result);
            return -1;
        }

        if (fdb_kv_get(&kvdb, "hello") != NULL) {
            log_e("mode3: hello still exists after delete.");
            return -1;
        }

        log_i("mode3: delete hello success.");
        return 0;
    }

    case 4: {
        struct fdb_kv_iterator itr;
        uint32_t count = 0;

        for (fdb_kv_iterator_init(&kvdb, &itr); fdb_kv_iterate(&kvdb, &itr);) {
            log_i("mode4: key=%s, value_len=%lu",
                  itr.curr_kv.name,
                  (unsigned long)itr.curr_kv.value_len);
            count++;
        }

        log_i("mode4: total keys=%lu", (unsigned long)count);
        return 0;
    }

    default:
        log_i("Usage: case_fdb <mode>");
        log_i("mode 1: string set/get");
        log_i("mode 2: blob set/get");
        log_i("mode 3: delete key");
        log_i("mode 4: iterate keys");
        fdb_kv_print(&kvdb);
        return 0;
    }
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_fdb,
                 case_fdb,
                 flashdb kvdb quick self-check);

#endif /* SDK_USING_TESTCASE_W25Q16 */
