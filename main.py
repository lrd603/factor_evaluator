from evaluator.metrics import calculate_ic


def main():
    factor_values = [0.2, 0.5, 0.8, 1.1, 1.5]
    future_returns = [0.01, 0.03, 0.04, 0.06, 0.08]

    ic = calculate_ic(factor_values, future_returns)

    print("Factor IC:", ic)


if __name__ == "__main__":
    main()