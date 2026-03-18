/**
 * @file    sgl_testcase.c
 * @brief   SGL shell testcase with multi-widget demo modes.
 */

#include "sgl.h"
#include "shell.h"
#include "elog.h"
#include <stdio.h>
#include <string.h>

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/sgl/"

#if defined(SDK_USING_TESTCASE_SGL)

typedef struct {
    sgl_obj_t *progress;
    sgl_obj_t *slider;
    sgl_obj_t *led;
    sgl_obj_t *ring;
    sgl_obj_t *value_label;
    sgl_obj_t *dot;
    char value_text[16];
} sgl_case_mode7_ctx_t;

static sgl_case_mode7_ctx_t g_mode7_ctx;
static sgl_anim_t *g_mode7_anim_main = NULL;
static sgl_anim_t *g_mode7_anim_pulse = NULL;

static void sgl_case_mode7_cleanup(void)
{
    if (g_mode7_anim_main != NULL) {
        sgl_anim_stop(g_mode7_anim_main);
        sgl_anim_free(g_mode7_anim_main);
        g_mode7_anim_main = NULL;
    }

    if (g_mode7_anim_pulse != NULL) {
        sgl_anim_stop(g_mode7_anim_pulse);
        sgl_anim_free(g_mode7_anim_pulse);
        g_mode7_anim_pulse = NULL;
    }

    memset(&g_mode7_ctx, 0, sizeof(g_mode7_ctx));
}

static int sgl_case_prepare_screen(sgl_obj_t **screen_out)
{
    sgl_obj_t *screen = sgl_screen_act();
    if (screen == NULL) {
        log_e("SGL is not ready.");
        return -1;
    }

    sgl_case_mode7_cleanup();
    sgl_obj_delete(NULL);
    sgl_page_set_color(screen, SGL_COLOR_BLACK);
    *screen_out = screen;
    return 0;
}

static void sgl_case_title(const char *text)
{
    sgl_obj_t *title = sgl_label_create(NULL);
    if (title == NULL) {
        return;
    }

    sgl_obj_set_size(title, 128, 18);
    sgl_obj_set_abs_pos(title, 0, 0);
    sgl_label_set_font(title, &consolas14);
    sgl_label_set_text_color(title, SGL_COLOR_YELLOW);
    sgl_label_set_text_align(title, SGL_ALIGN_TOP_MID);
    sgl_label_set_text(title, text);
}

static void sgl_case_mode7_main_anim_cb(sgl_anim_t *anim, int32_t value)
{
    sgl_case_mode7_ctx_t *ctx = (sgl_case_mode7_ctx_t *)anim->data;
    if (ctx == NULL) {
        return;
    }

    if (ctx->progress != NULL) {
        sgl_progress_set_value(ctx->progress, value);
    }

    if (ctx->slider != NULL) {
        sgl_slider_set_value(ctx->slider, value);
    }

    if (ctx->dot != NULL) {
        sgl_obj_set_abs_pos(ctx->dot, 12 + value, 98);
    }

    if (ctx->led != NULL) {
        if (value < 33) {
            sgl_led_set_on_color(ctx->led, SGL_COLOR_GREEN);
        } else if (value < 66) {
            sgl_led_set_on_color(ctx->led, SGL_COLOR_YELLOW);
        } else {
            sgl_led_set_on_color(ctx->led, SGL_COLOR_RED);
        }
        sgl_led_set_status(ctx->led, value >= 10);
    }

    if (ctx->ring != NULL) {
        if (value < 50) {
            sgl_ring_set_color(ctx->ring, SGL_COLOR_CYAN);
        } else {
            sgl_ring_set_color(ctx->ring, SGL_COLOR_ORANGE);
        }
    }

    if (ctx->value_label != NULL) {
        snprintf(ctx->value_text, sizeof(ctx->value_text), "VAL:%3d%%", value);
        sgl_label_set_text(ctx->value_label, ctx->value_text);
    }
}

static void sgl_case_mode7_pulse_anim_cb(sgl_anim_t *anim, int32_t value)
{
    sgl_case_mode7_ctx_t *ctx = (sgl_case_mode7_ctx_t *)anim->data;
    if (ctx == NULL || ctx->ring == NULL) {
        return;
    }

    sgl_ring_set_radius(ctx->ring, 8 + value / 20, 16 + value / 20);
}

int case_sgl(int mode)
{
    sgl_obj_t *screen = NULL;
    if (sgl_case_prepare_screen(&screen) != 0) {
        return -1;
    }

    switch (mode) {
    case 0: {
        sgl_case_title("MODE0 LABEL");
        sgl_obj_t *label = sgl_label_create(NULL);
        if (label == NULL) {
            log_e("Create label failed.");
            return -1;
        }
        sgl_obj_set_size(label, 128, 28);
        sgl_obj_set_pos_align(label, SGL_ALIGN_CENTER);
        sgl_label_set_font(label, &consolas24);
        sgl_label_set_text_color(label, SGL_COLOR_WHITE);
        sgl_label_set_text(label, "SGL TEST OK");
        log_i("SGL mode0 label.");
    } break;

    case 1: {
        sgl_case_title("MODE1 BUTTON");
        sgl_obj_t *btn = sgl_button_create(NULL);
        if (btn == NULL) {
            log_e("Create button failed.");
            return -1;
        }
        sgl_obj_set_size(btn, 96, 36);
        sgl_obj_set_pos_align(btn, SGL_ALIGN_CENTER);
        sgl_button_set_color(btn, SGL_COLOR_BLUE);
        sgl_button_set_border_color(btn, SGL_COLOR_WHITE);
        sgl_button_set_border_width(btn, 2);
        sgl_button_set_radius(btn, 6);
        sgl_button_set_text(btn, "BTN");
        sgl_button_set_text_color(btn, SGL_COLOR_WHITE);
        sgl_button_set_font(btn, &consolas24);
        log_i("SGL mode1 button.");
    } break;

    case 2: {
        sgl_case_title("MODE2 SLIDER");
        sgl_obj_t *slider = sgl_slider_create(NULL);
        if (slider == NULL) {
            log_e("Create slider failed.");
            return -1;
        }
        sgl_obj_set_size(slider, 100, 16);
        sgl_obj_set_abs_pos(slider, 14, 54);
        sgl_slider_set_radius(slider, 8);
        sgl_slider_set_track_color(slider, SGL_COLOR_DARK_GRAY);
        sgl_slider_set_fill_color(slider, SGL_COLOR_GREEN);
        sgl_slider_set_value(slider, 70);
        log_i("SGL mode2 slider.");
    } break;

    case 3: {
        sgl_case_title("MODE3 PROGRESS");
        sgl_obj_t *progress = sgl_progress_create(NULL);
        if (progress == NULL) {
            log_e("Create progress failed.");
            return -1;
        }
        sgl_obj_set_size(progress, 104, 22);
        sgl_obj_set_abs_pos(progress, 12, 52);
        sgl_progress_set_radius(progress, 11);
        sgl_progress_set_track_color(progress, SGL_COLOR_DARK_GRAY);
        sgl_progress_set_fill_color(progress, SGL_COLOR_ORANGE);
        sgl_progress_set_value(progress, 45);
        log_i("SGL mode3 progress.");
    } break;

    case 4: {
        sgl_case_title("MODE4 SWITCH+CHECK");
        sgl_obj_t *sw = sgl_switch_create(NULL);
        sgl_obj_t *cb = sgl_checkbox_create(NULL);
        if (sw == NULL || cb == NULL) {
            log_e("Create switch/checkbox failed.");
            return -1;
        }
        sgl_obj_set_size(sw, 56, 28);
        sgl_obj_set_abs_pos(sw, 12, 44);
        sgl_switch_set_status(sw, true);
        sgl_switch_set_color(sw, SGL_COLOR_GREEN);
        sgl_switch_set_bg_color(sw, SGL_COLOR_DARK_GRAY);
        sgl_switch_set_knob_color(sw, SGL_COLOR_WHITE);

        sgl_obj_set_size(cb, 88, 24);
        sgl_obj_set_abs_pos(cb, 12, 84);
        sgl_checkbox_set_font(cb, &consolas14);
        sgl_checkbox_set_text(cb, "ENABLE");
        sgl_checkbox_set_status(cb, true);
        sgl_checkbox_set_color(cb, SGL_COLOR_WHITE);
        log_i("SGL mode4 switch+checkbox.");
    } break;

    case 5: {
        sgl_case_title("MODE5 LED+RING");
        sgl_obj_t *led = sgl_led_create(NULL);
        sgl_obj_t *ring = sgl_ring_create(NULL);
        if (led == NULL || ring == NULL) {
            log_e("Create led/ring failed.");
            return -1;
        }

        sgl_obj_set_size(led, 22, 22);
        sgl_obj_set_abs_pos(led, 16, 52);
        sgl_led_set_status(led, true);
        sgl_led_set_on_color(led, SGL_COLOR_RED);
        sgl_led_set_bg_color(led, SGL_COLOR_DARK_GRAY);

        sgl_obj_set_size(ring, 46, 46);
        sgl_obj_set_abs_pos(ring, 68, 40);
        sgl_ring_set_color(ring, SGL_COLOR_CYAN);
        sgl_ring_set_radius(ring, 14, 22);
        log_i("SGL mode5 led+ring.");
    } break;

    case 6: {
        sgl_case_title("MODE6 RECT+LINE");
        sgl_obj_t *rect = sgl_rect_create(NULL);
        sgl_obj_t *line = sgl_line_create(NULL);
        if (rect == NULL || line == NULL) {
            log_e("Create rect/line failed.");
            return -1;
        }
        sgl_obj_set_size(rect, 80, 42);
        sgl_obj_set_abs_pos(rect, 8, 38);
        sgl_rect_set_color(rect, SGL_COLOR_BLUE);
        sgl_rect_set_border_color(rect, SGL_COLOR_WHITE);
        sgl_rect_set_border_width(rect, 2);
        sgl_rect_set_radius(rect, 6);

        sgl_obj_set_size(line, 1, 1);
        sgl_line_set_pos(line, 8, 94, 120, 116);
        sgl_line_set_color(line, SGL_COLOR_YELLOW);
        sgl_line_set_width(line, 2);
        log_i("SGL mode6 rect+line.");
    } break;

    case 7: {
        sgl_case_title("MODE7 ANIMATION");
        memset(&g_mode7_ctx, 0, sizeof(g_mode7_ctx));

        g_mode7_ctx.progress = sgl_progress_create(NULL);
        g_mode7_ctx.slider = sgl_slider_create(NULL);
        g_mode7_ctx.led = sgl_led_create(NULL);
        g_mode7_ctx.ring = sgl_ring_create(NULL);
        g_mode7_ctx.value_label = sgl_label_create(NULL);
        g_mode7_ctx.dot = sgl_rect_create(NULL);

        if (g_mode7_ctx.progress == NULL || g_mode7_ctx.slider == NULL ||
            g_mode7_ctx.led == NULL || g_mode7_ctx.ring == NULL ||
            g_mode7_ctx.value_label == NULL || g_mode7_ctx.dot == NULL) {
            log_e("Create mode7 widgets failed.");
            return -1;
        }

        sgl_obj_set_size(g_mode7_ctx.progress, 104, 18);
        sgl_obj_set_abs_pos(g_mode7_ctx.progress, 12, 28);
        sgl_progress_set_radius(g_mode7_ctx.progress, 9);
        sgl_progress_set_track_color(g_mode7_ctx.progress, SGL_COLOR_DARK_GRAY);
        sgl_progress_set_fill_color(g_mode7_ctx.progress, SGL_COLOR_CYAN);
        sgl_progress_set_value(g_mode7_ctx.progress, 0);

        sgl_obj_set_size(g_mode7_ctx.slider, 104, 14);
        sgl_obj_set_abs_pos(g_mode7_ctx.slider, 12, 56);
        sgl_slider_set_radius(g_mode7_ctx.slider, 7);
        sgl_slider_set_track_color(g_mode7_ctx.slider, SGL_COLOR_DARK_GRAY);
        sgl_slider_set_fill_color(g_mode7_ctx.slider, SGL_COLOR_GREEN);
        sgl_slider_set_value(g_mode7_ctx.slider, 0);

        sgl_obj_set_size(g_mode7_ctx.led, 20, 20);
        sgl_obj_set_abs_pos(g_mode7_ctx.led, 12, 78);
        sgl_led_set_bg_color(g_mode7_ctx.led, SGL_COLOR_DARK_GRAY);
        sgl_led_set_on_color(g_mode7_ctx.led, SGL_COLOR_GREEN);
        sgl_led_set_status(g_mode7_ctx.led, true);

        sgl_obj_set_size(g_mode7_ctx.ring, 42, 42);
        sgl_obj_set_abs_pos(g_mode7_ctx.ring, 72, 74);
        sgl_ring_set_color(g_mode7_ctx.ring, SGL_COLOR_CYAN);
        sgl_ring_set_radius(g_mode7_ctx.ring, 10, 18);

        sgl_obj_set_size(g_mode7_ctx.value_label, 64, 16);
        sgl_obj_set_abs_pos(g_mode7_ctx.value_label, 34, 80);
        sgl_label_set_font(g_mode7_ctx.value_label, &consolas14);
        sgl_label_set_text_color(g_mode7_ctx.value_label, SGL_COLOR_WHITE);
        sgl_label_set_text(g_mode7_ctx.value_label, "VAL:  0%");

        sgl_obj_set_size(g_mode7_ctx.dot, 6, 6);
        sgl_obj_set_abs_pos(g_mode7_ctx.dot, 12, 98);
        sgl_rect_set_color(g_mode7_ctx.dot, SGL_COLOR_YELLOW);
        sgl_rect_set_border_width(g_mode7_ctx.dot, 0);
        sgl_rect_set_radius(g_mode7_ctx.dot, 3);

        g_mode7_anim_main = sgl_anim_create();
        g_mode7_anim_pulse = sgl_anim_create();
        if (g_mode7_anim_main == NULL || g_mode7_anim_pulse == NULL) {
            log_e("Create mode7 animation failed.");
            sgl_case_mode7_cleanup();
            return -1;
        }

        sgl_anim_set_data(g_mode7_anim_main, &g_mode7_ctx);
        sgl_anim_set_act_duration(g_mode7_anim_main, 2400);
        sgl_anim_set_start_value(g_mode7_anim_main, 0);
        sgl_anim_set_end_value(g_mode7_anim_main, 100);
        sgl_anim_set_repeat_cnt(g_mode7_anim_main, SGL_ANIM_REPEAT_LOOP);
        sgl_anim_set_path(g_mode7_anim_main, sgl_case_mode7_main_anim_cb, SGL_ANIM_PATH_EASE_IN_OUT);
        sgl_anim_start(g_mode7_anim_main);

        sgl_anim_set_data(g_mode7_anim_pulse, &g_mode7_ctx);
        sgl_anim_set_act_duration(g_mode7_anim_pulse, 900);
        sgl_anim_set_start_value(g_mode7_anim_pulse, 0);
        sgl_anim_set_end_value(g_mode7_anim_pulse, 100);
        sgl_anim_set_repeat_cnt(g_mode7_anim_pulse, SGL_ANIM_REPEAT_LOOP);
        sgl_anim_set_path(g_mode7_anim_pulse, sgl_case_mode7_pulse_anim_cb, SGL_ANIM_PATH_EASE_IN_OUT);
        sgl_anim_start(g_mode7_anim_pulse);

        log_i("SGL mode7 rich animation.");
    } break;

    default:
        log_i("Usage: case_sgl <mode>");
        log_i("  mode 0: label");
        log_i("  mode 1: button");
        log_i("  mode 2: slider");
        log_i("  mode 3: progress");
        log_i("  mode 4: switch + checkbox");
        log_i("  mode 5: led + ring");
        log_i("  mode 6: rect + line");
        log_i("  mode 7: animation");
        return -1;
    }

    sgl_task_handle_sync();
    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_sgl,
                 case_sgl,
                 test sgl render);

#endif /* SDK_USING_TESTCASE_SGL */
