import unittest
import pandas as pd

from lib import *

df_full = load_data_full()
df = get_data_section(df_full)


class TestGetNextDate(unittest.TestCase):
    def test_existing_date_returned_as_is(self):
        result = get_next_date(df, "2021-03-01")
        self.assertEqual(result, "2021-03-01")

    def test_weekend_returns_next_trading_day(self):
        # 2021-03-06 is a Saturday; next trading day should be after it
        result = get_next_date(df, "2021-03-06")
        self.assertIsNotNone(result)
        self.assertGreater(pd.Timestamp(result), pd.Timestamp("2021-03-06"))

    def test_date_beyond_dataset_returns_none(self):
        result = get_next_date(df, "2099-01-01")
        self.assertIsNone(result)

    def test_returns_string_in_yyyy_mm_dd_format(self):
        result = get_next_date(df, "2021-03-01")
        self.assertIsInstance(result, str)
        self.assertRegex(result, r"^\d{4}-\d{2}-\d{2}$")


class TestUnderlyingAt(unittest.TestCase):
    def test_returns_positive_float_for_valid_date(self):
        result = underlying_at(df, "2021-03-01")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, float)
        self.assertGreater(result, 0)

    def test_returns_none_for_date_not_in_dataset(self):
        result = underlying_at(df, "1900-01-01")
        self.assertIsNone(result)


class TestQuoteAt(unittest.TestCase):
    def test_returns_row_for_valid_put(self):
        result = quote_at(df, "2021-03-01", target_delta=0.3, target_dte=30, side="P")
        self.assertIsNotNone(result)

    def test_returns_row_for_valid_call(self):
        result = quote_at(df, "2021-03-01", target_delta=0.3, target_dte=30, side="C")
        self.assertIsNotNone(result)

    def test_put_delta_is_negative(self):
        result = quote_at(df, "2021-03-01", target_delta=0.3, target_dte=30, side="P")
        self.assertLess(float(result["P_DELTA"]), 0)

    def test_call_delta_is_positive(self):
        result = quote_at(df, "2021-03-01", target_delta=0.3, target_dte=30, side="C")
        self.assertGreater(float(result["C_DELTA"]), 0)

    def test_invalid_side_raises_value_error(self):
        with self.assertRaises(ValueError):
            quote_at(df, "2021-03-01", target_delta=0.3, target_dte=30, side="X")

    def test_returns_none_for_date_not_in_dataset(self):
        result = quote_at(df, "1900-01-01", target_delta=0.3, target_dte=30, side="P")
        self.assertIsNone(result)


class TestQuoteAtStrike(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        open_quote     = quote_at(df, "2021-03-01", target_delta=0.3, target_dte=30, side="P")
        cls.strike     = open_quote["STRIKE"]
        cls.expiration = open_quote["EXPIRE_DATE"]
        cls.close_date = get_next_date(df, pd.to_datetime("2021-03-01") + pd.Timedelta(days=10))

    def test_returns_row_for_valid_inputs(self):
        result = quote_at_strike(df, self.close_date,
                                 expiration=self.expiration, strike=self.strike)
        self.assertIsNotNone(result)

    def test_returned_row_has_matching_strike(self):
        result = quote_at_strike(df, self.close_date,
                                 expiration=self.expiration, strike=self.strike)
        self.assertEqual(float(result["STRIKE"]), float(self.strike))

    def test_returned_row_has_matching_expiration(self):
        result = quote_at_strike(df, self.close_date,
                                 expiration=self.expiration, strike=self.strike)
        self.assertEqual(result["EXPIRE_DATE"], self.expiration)

    def test_returns_none_for_nonexistent_strike(self):
        result = quote_at_strike(df, self.close_date,
                                 expiration=self.expiration, strike=999999.0)
        self.assertIsNone(result)


class TestComputeTrade(unittest.TestCase):
    def _make_quotes(self, delta, days):
        quote_open = quote_at(df, "2021-03-01", target_delta=delta, target_dte=30, side="P")
        close_date = get_next_date(df, pd.to_datetime("2021-03-01") + pd.Timedelta(days=days))
        quote_close = quote_at_strike(df, close_date,
                                      expiration=quote_open["EXPIRE_DATE"],
                                      strike=quote_open["STRIKE"])
        return quote_open, quote_close

    def test_returns_four_values(self):
        quote_open, quote_close = self._make_quotes(delta=0.3, days=10)
        result = compute_trade(quote_open, quote_close)
        self.assertEqual(len(result), 4)

    def test_assigned_is_bool(self):
        quote_open, quote_close = self._make_quotes(delta=0.3, days=10)
        assigned, *_ = compute_trade(quote_open, quote_close)
        self.assertIsInstance(assigned, bool)

    @unittest.skip("to review")
    def test_pl_values_are_floats(self):
        quote_open, quote_close = self._make_quotes(delta=0.3, days=10)
        assigned, total_pl, premium_pl, valuation_pl = compute_trade(quote_open, quote_close)
        self.assertIsInstance(total_pl, float)
        self.assertIsInstance(premium_pl, float)
        self.assertIsInstance(valuation_pl, float)

    def test_in_the_money_case(self):
        quote_open, quote_close = self._make_quotes(delta=0.5, days=10)
        assigned, total_pl, premium_pl, valuation_pl = compute_trade(quote_open, quote_close)
        self.assertIsInstance(assigned, bool)
        self.assertIsInstance(total_pl, float)

    def test_at_expiration_case(self):
        quote_open = quote_at(df, "2021-03-01", target_delta=0.5, target_dte=30, side="P")
        expiration = quote_open["EXPIRE_DATE"]
        quote_close = quote_at_strike(df, expiration,
                                      expiration=expiration,
                                      strike=quote_open["STRIKE"])
        if quote_close is None:
            self.skipTest("No close quote available at expiration for this test date")
        assigned, total_pl, premium_pl, valuation_pl = compute_trade(quote_open, quote_close)
        self.assertIsInstance(assigned, bool)
        self.assertIsInstance(total_pl, float)

@unittest.skip("to review")
class TestDisplayChain(unittest.TestCase):
    def test_returns_dataframe_for_valid_inputs(self):
        result = display_chain(df_full, "2021-03-01", dte=30, delta_min=0.3, delta_max=0.5)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)

    def test_filtered_dte_is_approximately_correct(self):
        chain_all = display_chain(df, "2021-03-01")
        target_dte = int(chain_all["DTE"].round().iloc[0])
        result = display_chain(df, "2021-03-01", dte=target_dte)
        self.assertIsNotNone(result)
        self.assertTrue((result["DTE"].round() == target_dte).all())

    def test_returns_none_for_date_not_in_dataset(self):
        result = display_chain(df_full, "1900-01-01")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
