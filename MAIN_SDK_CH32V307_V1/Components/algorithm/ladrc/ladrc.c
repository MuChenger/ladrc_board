#include "ladrc.h"
#include "ladrc_params.h"

// https://blog.csdn.net/weixin_41276397/article/details/127353049
// https://www.zhihu.com/topic/21674178/hot?utm_id=0
// https://zhuanlan.zhihu.com/p/671470218

LADRC_TypeDef M1_Sysparam;
LADRC_TypeDef M2_Sysparam;
LADRC_TypeDef M3_Sysparam;
LADRC_TypeDef M4_Sysparam;

const double LADRC_Unit[5][5] =
{
    {0.05, 20, 100, 400, 0.5},
    {0.02, 20, 2, 40, 0.5},
    {0.05, 100, 20, 80, 0.5},
    {0.05, 100, 14, 57, 0.5},
    {0.05, 100, 50, 10, 1}
};

void LADRC_INIT(LADRC_TypeDef *LADRC_Para)
{
    LADRC_Para->h = LADRC_Unit[1][0];
    LADRC_Para->r = LADRC_Unit[1][1];
    LADRC_Para->wc = LADRC_Unit[1][2];
    LADRC_Para->w0 = LADRC_Unit[1][3];
    LADRC_Para->b0 = LADRC_Unit[1][4];
    LADRC_Para->v1 = 0;
    LADRC_Para->v2 = 0;
    LADRC_Para->z1 = 0;
    LADRC_Para->z2 = 0;
    LADRC_Para->z3 = 0;
    LADRC_Para->u = 0;
}

void LADRC_REST(LADRC_TypeDef *LADRC_Para)
{
    LADRC_Para->r = 0;
    LADRC_Para->v1 = 0;
    LADRC_Para->v2 = 0;
    LADRC_Para->w0 = 0;
    LADRC_Para->b0 = 0;
    LADRC_Para->u = 0;
    LADRC_Para->z1 = 0;
    LADRC_Para->z2 = 0;
    LADRC_Para->z3 = 0;
}

void LADRC_TD(LADRC_TypeDef *LADRC_Para, double Expect)
{
    double fh = -LADRC_Para->r * LADRC_Para->r * (LADRC_Para->v1 - Expect) - 2 * LADRC_Para->r * LADRC_Para->v2;
    LADRC_Para->v1 += LADRC_Para->v2 * LADRC_Para->h;
    LADRC_Para->v2 += fh * LADRC_Para->h;
}

void LADRC_ESO(LADRC_TypeDef *LADRC_Para, double FeedBack)
{
    double Beita_01 = 3 * LADRC_Para->w0;
    double Beita_02 = 3 * LADRC_Para->w0 * LADRC_Para->w0;
    double Beita_03 = LADRC_Para->w0 * LADRC_Para->w0 * LADRC_Para->w0;
    double e = LADRC_Para->z1 - FeedBack;

    LADRC_Para->z1 += (LADRC_Para->z2 - Beita_01 * e) * LADRC_Para->h;
    LADRC_Para->z2 += (LADRC_Para->z3 - Beita_02 * e + LADRC_Para->b0 * LADRC_Para->u) * LADRC_Para->h;
    LADRC_Para->z3 += -Beita_03 * e * LADRC_Para->h;
}

void LADRC_LF(LADRC_TypeDef *LADRC_Para)
{
    double wc;
    double Kp;
    double Kd;
    double e1;
    double e2;
    double u0;

#if (LADRC_WC_MODE == LADRC_WC_MODE_FROM_W0_DIV4)
    wc = LADRC_Para->w0 / 4.0;
#else
    wc = (LADRC_Para->wc > 0.0) ? LADRC_Para->wc : (LADRC_Para->w0 / 4.0);
#endif

    LADRC_Para->wc = wc;
    Kp = wc * wc;
    Kd = 2 * wc;
    e1 = LADRC_Para->v1 - LADRC_Para->z1;
    e2 = LADRC_Para->v2 - LADRC_Para->z2;
    u0 = Kp * e1 + Kd * e2;
    LADRC_Para->u = (u0 - LADRC_Para->z3) / LADRC_Para->b0;

    if (LADRC_Para->u > RealTimeOut_Threshold) {
        LADRC_Para->u = RealTimeOut_Threshold;
    } else if (LADRC_Para->u < -RealTimeOut_Threshold) {
        LADRC_Para->u = -RealTimeOut_Threshold;
    }
}

void LADRC_Loop(LADRC_TypeDef *LADRC_Para, double *Expect, double *RealTimeOut)
{
    double Expect_Value = *Expect;
    double Measure = *RealTimeOut;

    LADRC_TD(LADRC_Para, Expect_Value);
    LADRC_ESO(LADRC_Para, Measure);
    LADRC_LF(LADRC_Para);
}
