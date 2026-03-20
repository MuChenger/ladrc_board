#ifndef _FAL_CFG_H_
#define _FAL_CFG_H_

int flashdb_printf(const char *fmt, ...);
#define FAL_PRINTF flashdb_printf
struct fal_flash_dev;

/* Use static partition table from this file. */
#define FAL_PART_HAS_TABLE_CFG

/* External SFUD-backed NOR flash device. */
extern struct fal_flash_dev nor_flash0;

/* Flash device table. */
#define FAL_FLASH_DEV_TABLE            \
    {                                  \
        &nor_flash0,                   \
    }

/*
 * W25Q16 total size is 2MB. Reserve two 512KB regions for FlashDB by default.
 * Offsets and lengths are erase-block aligned (4KB).
 */
#define FAL_PART_TABLE                                                                 \
    {                                                                                  \
        {FAL_PART_MAGIC_WORD, "fdb_tsdb1", "norflash0", 0 * 1024 * 1024, 512 * 1024, 0}, \
        {FAL_PART_MAGIC_WORD, "fdb_kvdb1", "norflash0", 1 * 1024 * 1024, 512 * 1024, 0}, \
    }

#endif /* _FAL_CFG_H_ */
