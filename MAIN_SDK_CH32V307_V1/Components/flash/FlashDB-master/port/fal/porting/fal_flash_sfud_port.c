#include <fal.h>
#include <sfud.h>

#ifndef FAL_USING_NOR_FLASH_DEV_NAME
#define FAL_USING_NOR_FLASH_DEV_NAME "norflash0"
#endif

static int sfud_flash_init(void);
static int sfud_flash_read(long offset, uint8_t *buf, size_t size);
static int sfud_flash_write(long offset, const uint8_t *buf, size_t size);
static int sfud_flash_erase(long offset, size_t size);

static sfud_flash *g_sfud_dev = NULL;
static uint8_t g_sfud_inited = 0;

struct fal_flash_dev nor_flash0 = {
    .name = FAL_USING_NOR_FLASH_DEV_NAME,
    .addr = 0,
    .len = 2 * 1024 * 1024,
    .blk_size = 4096,
    .ops = {sfud_flash_init, sfud_flash_read, sfud_flash_write, sfud_flash_erase},
    .write_gran = 1,
};

static int sfud_flash_init(void)
{
    sfud_err result;

    if (!g_sfud_inited) {
        result = sfud_init();
        if (result != SFUD_SUCCESS) {
            return -1;
        }
        g_sfud_inited = 1;
    }

    g_sfud_dev = sfud_get_device(0);
    if (g_sfud_dev == NULL || !g_sfud_dev->init_ok) {
        return -1;
    }

    /* Sync FAL geometry with detected flash chip info. */
    nor_flash0.blk_size = g_sfud_dev->chip.erase_gran;
    nor_flash0.len = g_sfud_dev->chip.capacity;

    return 0;
}

static int sfud_flash_read(long offset, uint8_t *buf, size_t size)
{
    if (g_sfud_dev == NULL || !g_sfud_dev->init_ok) {
        return -1;
    }
    if (sfud_read(g_sfud_dev, nor_flash0.addr + offset, size, buf) != SFUD_SUCCESS) {
        return -1;
    }
    return (int)size;
}

static int sfud_flash_write(long offset, const uint8_t *buf, size_t size)
{
    if (g_sfud_dev == NULL || !g_sfud_dev->init_ok) {
        return -1;
    }
    if (sfud_write(g_sfud_dev, nor_flash0.addr + offset, size, buf) != SFUD_SUCCESS) {
        return -1;
    }
    return (int)size;
}

static int sfud_flash_erase(long offset, size_t size)
{
    if (g_sfud_dev == NULL || !g_sfud_dev->init_ok) {
        return -1;
    }
    if (sfud_erase(g_sfud_dev, nor_flash0.addr + offset, size) != SFUD_SUCCESS) {
        return -1;
    }
    return (int)size;
}

