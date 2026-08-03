def generate_report(
    daily_ic,
    daily_rank_ic,
    icir
):
    """
    生成因子评价报告
    """

    ic_mean = daily_ic.mean()
    ic_std = daily_ic.std()

    rank_ic_mean = daily_rank_ic.mean()


    print("========================")
    print("Factor Evaluation Report")
    print("========================")


    print(f"\nIC Mean: {ic_mean:.4f}")

    print(f"IC Std: {ic_std:.4f}")

    print(f"ICIR: {icir:.4f}")

    print(f"Rank IC Mean: {rank_ic_mean:.4f}")


    if icir > 1:
        quality = "Strong"
    elif icir > 0.5:
        quality = "Medium"
    else:
        quality = "Weak"


    print("\nFactor Quality:")
    print(quality)

    print("========================")