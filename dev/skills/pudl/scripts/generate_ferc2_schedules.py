#!/usr/bin/env python3
"""Generate ferc2_schedules.json from the blank FERC Form 2 HTML and XBRL table names."""

import json
import re
from bs4 import BeautifulSoup

HTML_PATH = (
    "/Users/zane/code/catalyst/pudl/docs/data_sources/ferc2/ferc2_blank_2025-07-31.html"
)
OUTPUT_PATH = (
    "/Users/zane/code/catalyst/agent-skills/skills/pudl/assets/ferc2_schedules.json"
)

# All XBRL table names
XBRL_TABLES = [
    "accumulated_deferred_income_taxes_account_190_classified_by_business_activities_234_duration",
    "accumulated_deferred_income_taxes_account_190_classified_by_business_activities_234_instant",
    "accumulated_deferred_income_taxes_account_190_classified_by_tax_types_234_duration",
    "accumulated_deferred_income_taxes_account_190_classified_by_tax_types_234_instant",
    "accumulated_deferred_income_taxes_other_account_283_classified_by_business_activities_276_duration",
    "accumulated_deferred_income_taxes_other_account_283_classified_by_business_activities_276_instant",
    "accumulated_deferred_income_taxes_other_account_283_classified_by_tax_types_276_duration",
    "accumulated_deferred_income_taxes_other_account_283_classified_by_tax_types_276_instant",
    "accumulated_deferred_income_taxes_other_property_account_282_classified_by_business_activities_274_duration",
    "accumulated_deferred_income_taxes_other_property_account_282_classified_by_business_activities_274_instant",
    "accumulated_deferred_income_taxes_other_property_account_282_classified_by_tax_types_274_duration",
    "accumulated_deferred_income_taxes_other_property_account_282_classified_by_tax_types_274_instant",
    "accumulated_provision_for_depreciation_of_gas_utility_plant_account_108_other_accounts_219_duration",
    "accumulated_provision_for_depreciation_of_gas_utility_plant_account_108_other_debit_or_credit_items_219_duration",
    "accumulated_provision_for_depreciation_of_gas_utility_plant_account_108_section_a_219_duration",
    "accumulated_provision_for_depreciation_of_gas_utility_plant_account_108_section_a_219_instant",
    "accumulated_provision_for_depreciation_of_gas_utility_plant_account_108_section_b_219_instant",
    "auxiliary_peaking_facilities_519_duration",
    "capital_stock_accounts_201_and_204_250_duration",
    "capital_stock_accounts_201_and_204_250_instant",
    "capital_stock_accounts_201_and_204_totals_250_instant",
    "capital_stock_common_stock_account_201_250_duration",
    "capital_stock_common_stock_account_201_250_instant",
    "capital_stock_common_stock_account_201_totals_250_instant",
    "capital_stock_common_stock_converted_account_203_252_duration",
    "capital_stock_common_stock_converted_account_203_252_instant",
    "capital_stock_common_stock_subscribed_account_202_252_duration",
    "capital_stock_common_stock_subscribed_account_202_252_instant",
    "capital_stock_expense_account_214_254_duration",
    "capital_stock_expense_account_214_254_instant",
    "capital_stock_expense_account_214_totals_254_instant",
    "capital_stock_installments_on_capital_stock_account_212_252_duration",
    "capital_stock_installments_on_capital_stock_account_212_252_instant",
    "capital_stock_installments_on_capital_stock_account_212_totals_252_instant",
    "capital_stock_preferred_stock_account_204_250_duration",
    "capital_stock_preferred_stock_account_204_250_instant",
    "capital_stock_preferred_stock_account_204_totals_250_instant",
    "capital_stock_preferred_stock_liability_for_conversion_account_206_252_duration",
    "capital_stock_preferred_stock_liability_for_conversion_account_206_252_instant",
    "capital_stock_preferred_stock_subscribed_account_205_252_duration",
    "capital_stock_preferred_stock_subscribed_account_205_252_instant",
    "capital_stock_premium_on_capital_stock_account_207_252_duration",
    "capital_stock_premium_on_capital_stock_account_207_252_instant",
    "capital_stock_premium_on_capital_stock_account_207_totals_252_instant",
    "capital_stock_subscribed_liability_for_conversion_premium_on_and_installments_recieved_on_accts_202_203_205_206_207_and_212_252_duration",
    "capital_stock_subscribed_liability_for_conversion_premium_on_and_installments_recieved_on_accts_202_203_205_206_207_and_212_252_instant",
    "capital_stock_subscribed_liability_for_conversion_premium_on_and_installments_recieved_on_accts_202_203_205_206_207_and_212_totals_252_instant",
    "charges_for_outside_professional_and_other_consultative_services_357_duration",
    "charges_for_outside_professional_and_other_consultative_services_totals_357_duration",
    "comparative_balance_sheet_assets_and_other_debits_110_instant",
    "comparative_balance_sheet_liabilities_and_other_credits_110_instant",
    "compressor_stations_508_duration",
    "compressor_stations_total_508_duration",
    "construction_work_in_progress_gas_216_instant",
    "construction_work_in_progress_gas_details_216_duration",
    "construction_work_in_progress_gas_details_216_instant",
    "control_over_respondent_102_duration",
    "control_over_respondent_102_instant",
    "corporate_officer_certification_001_duration",
    "corporations_controlled_by_respondent_103_duration",
    "corporations_controlled_by_respondent_103_instant",
    "depreciation_depletion_and_amortization_of_gas_plant_section_a_336_duration",
    "depreciation_depletion_and_amortization_of_gas_plant_section_b_336_duration",
    "depreciation_depletion_and_amortization_of_gas_plant_section_b_details_336_duration",
    "discount_on_capital_stock_account_213_254_duration",
    "discount_on_capital_stock_account_213_254_instant",
    "discount_on_capital_stock_account_213_totals_254_instant",
    "discount_on_long_term_debt_account_226_258_duration",
    "discount_on_long_term_debt_account_226_258_instant",
    "discounted_rate_services_and_negotiated_rate_services_313_duration",
    "discounted_rate_services_and_negotiated_rate_services_totals_313_duration",
    "distribution_of_salaries_and_wages_354_duration",
    "distribution_of_salaries_and_wages_other_account_details_354_duration",
    "employee_pensions_and_benefits_account_926_352_duration",
    "employee_pensions_and_benefits_account_926_breakdown_352_duration",
    "exchange_and_imbalance_transactions_328_duration",
    "exchange_and_imbalance_transactions_totals_328_duration",
    "extraordinary_property_losses_account_182_1_230b_duration",
    "extraordinary_property_losses_account_182_1_230b_instant",
    "extraordinary_property_losses_account_182_1_totals_230b_instant",
    "gas_account_natural_gas_520_duration",
    "gas_account_natural_gas_delivered_for_other_operations_520_duration",
    "gas_account_natural_gas_received_from_other_operations_520_duration",
    "gas_operating_revenues_300_duration",
    "gas_operation_and_maintenance_expense_317_duration",
    "gas_plant_held_for_future_use_214_duration",
    "gas_plant_held_for_future_use_214_instant",
    "gas_plant_held_for_future_use_totals_214_instant",
    "gas_plant_in_services_204_duration",
    "gas_plant_in_services_204_instant",
    "gas_property_and_capacity_leased_from_others_212_duration",
    "gas_property_and_capacity_leased_from_others_totals_212_duration",
    "gas_property_and_capacity_leased_to_others_213_duration",
    "gas_property_and_capacity_leased_to_others_totals_213_duration",
    "gas_storage_projects_by_capacities_513_duration",
    "gas_storage_projects_by_months_gas_delivered_to_storage_512_duration",
    "gas_storage_projects_by_months_gas_withdrawn_from_storage_512_duration",
    "gas_stored_220_duration",
    "gas_stored_220_instant",
    "gas_used_in_utility_operations_331_duration",
    "gas_used_in_utility_operations_totals_331_duration",
    "general_description_of_construction_overhead_procedure_rate_218_instant",
    "general_description_of_construction_overhead_procedure_table_218_duration",
    "general_description_of_construction_overhead_procedure_table_218_instant",
    "general_information_101_duration",
    "identification_001_duration",
    "important_changes_during_the_quarter_year_108_1_duration",
    "investments_account_123_124_and_136_222_duration",
    "investments_account_123_124_and_136_222_instant",
    "investments_account_123_124_and_136_totals_222_duration",
    "investments_account_123_124_and_136_totals_222_instant",
    "investments_in_associated_companies_account_123_222_duration",
    "investments_in_associated_companies_account_123_222_instant",
    "investments_in_associated_companies_account_123_totals_222_duration",
    "investments_in_associated_companies_account_123_totals_222_instant",
    "investments_in_other_investments_account_124_222_duration",
    "investments_in_other_investments_account_124_222_instant",
    "investments_in_other_investments_account_124_totals_222_duration",
    "investments_in_other_investments_account_124_totals_222_instant",
    "investments_in_subsidiary_companies_account_123_1_224_duration",
    "investments_in_subsidiary_companies_account_123_1_224_instant",
    "investments_in_subsidiary_companies_account_123_1_totals_224_duration",
    "investments_in_subsidiary_companies_account_123_1_totals_224_instant",
    "list_of_schedules_002_duration",
    "long_term_debt_accounts_221_222_223_and_224_256_duration",
    "long_term_debt_accounts_221_222_223_and_224_256_instant",
    "long_term_debt_accounts_221_222_223_and_224_totals_256_duration",
    "long_term_debt_accounts_221_222_223_and_224_totals_256_instant",
    "long_term_debt_advances_from_associated_companies_223_256_duration",
    "long_term_debt_advances_from_associated_companies_223_256_instant",
    "long_term_debt_advances_from_associated_companies_223_totals_256_duration",
    "long_term_debt_advances_from_associated_companies_223_totals_256_instant",
    "long_term_debt_bonds_221_256_duration",
    "long_term_debt_bonds_221_256_instant",
    "long_term_debt_bonds_221_totals_256_duration",
    "long_term_debt_bonds_221_totals_256_instant",
    "long_term_debt_other_long_term_debt_224_256_duration",
    "long_term_debt_other_long_term_debt_224_256_instant",
    "long_term_debt_other_long_term_debt_224_totals_256_duration",
    "long_term_debt_other_long_term_debt_224_totals_256_instant",
    "long_term_debt_reacquired_bonds_222_256_duration",
    "long_term_debt_reacquired_bonds_222_256_instant",
    "long_term_debt_reacquired_bonds_222_totals_256_duration",
    "long_term_debt_reacquired_bonds_222_totals_256_instant",
    "miscellaneous_current_and_accrued_liabilities_account_242_268_duration",
    "miscellaneous_current_and_accrued_liabilities_account_242_268_instant",
    "miscellaneous_current_and_accrued_liabilities_account_242_totals_268_instant",
    "miscellaneous_deferred_debits_account_186_233_duration",
    "miscellaneous_deferred_debits_account_186_233_instant",
    "miscellaneous_deferred_debits_account_186_totals_233_duration",
    "miscellaneous_deferred_debits_account_186_totals_233_instant",
    "miscellaneous_general_expenses_account_930_2_335_duration",
    "miscellaneous_general_expenses_account_930_2_breakdown_335_duration",
    "monthly_quantity_revenue_data_by_rate_schedule_299_duration",
    "monthly_quantity_revenue_data_by_rate_schedule_storage_299_duration",
    "monthly_quantity_revenue_data_by_rate_schedule_transportation_299_duration",
    "non_traditional_rate_treatment_afforded_new_projects_217_duration",
    "non_traditional_rate_treatment_afforded_new_projects_217_instant",
    "non_traditional_rate_treatment_afforded_new_projects_totals_217_duration",
    "non_traditional_rate_treatment_afforded_new_projects_totals_217_instant",
    "notes_to_financial_statements_122_1_duration",
    "other_deferred_credits_account_253_269_duration",
    "other_deferred_credits_account_253_269_instant",
    "other_deferred_credits_account_253_totals_269_duration",
    "other_deferred_credits_account_253_totals_269_instant",
    "other_gas_revenues_account_495_308_duration",
    "other_gas_revenues_account_495_breakdown_308_duration",
    "other_gas_supply_expenses_account_813_334_duration",
    "other_gas_supply_expenses_account_813_totals_334_duration",
    "other_paid_in_capital_accounts_208_211_253_duration",
    "other_paid_in_capital_accounts_208_211_donations_received_from_stockholders_253_duration",
    "other_paid_in_capital_accounts_208_211_miscellaneous_paid_in_capital_253_duration",
    "other_paid_in_capital_accounts_208_211_reduction_in_par_or_stated_value_of_capital_stock_253_duration",
    "other_paid_in_capital_accounts_208_211_required_capital_stock_253_duration",
    "other_paid_in_capital_accounts_208_211_total_253_duration",
    "other_paid_in_capital_accounts_208_211_total_253_instant",
    "other_regulatory_assets_account_182_3_232_duration",
    "other_regulatory_assets_account_182_3_232_instant",
    "other_regulatory_assets_account_182_3_totals_232_duration",
    "other_regulatory_assets_account_182_3_totals_232_instant",
    "other_regulatory_liabilities_278_duration",
    "other_regulatory_liabilities_278_instant",
    "other_regulatory_liabilities_totals_278_duration",
    "other_regulatory_liabilities_totals_278_instant",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_donations_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_donations_totals_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_interest_on_debt_to_associated_companies_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_interest_on_debt_to_associated_companies_totals_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_life_insurance_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_life_insurance_totals_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_miscellaneous_amortization_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_miscellaneous_amortization_totals_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_other_deductions_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_other_deductions_totals_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_other_interest_expense_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_other_interest_expense_totals_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_penalties_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_penalties_totals_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_political_and_related_activities_340_duration",
    "particulars_concerning_certain_income_deductions_and_interest_charges_accounts_political_and_related_activities_totals_340_duration",
    "premium_on_long_term_debt_account_225_258_duration",
    "premium_on_long_term_debt_account_225_258_instant",
    "prepayments_account_165_230a_instant",
    "reconciliation_of_reported_net_income_with_taxable_income_for_federal_income_taxes_261_duration",
    "reconciliation_of_reported_net_income_with_taxable_income_for_federal_income_taxes_deductions_on_return_not_charged_against_book_income_261_duration",
    "reconciliation_of_reported_net_income_with_taxable_income_for_federal_income_taxes_deductions_recorded_on_books_not_deducted_for_return_261_duration",
    "reconciliation_of_reported_net_income_with_taxable_income_for_federal_income_taxes_income_recorded_on_books_not_included_in_return_261_duration",
    "reconciliation_of_reported_net_income_with_taxable_income_for_federal_income_taxes_show_computation_of_tax_261_duration",
    "reconciliation_of_reported_net_income_with_taxable_income_for_federal_income_taxes_taxable_income_not_reported_on_books_261_duration",
    "regulatory_commission_expenses_account_928_350_duration",
    "regulatory_commission_expenses_account_928_350_instant",
    "regulatory_commission_expenses_account_928_total_350_duration",
    "regulatory_commission_expenses_account_928_total_350_instant",
    "retained_earnings_118_duration",
    "retained_earnings_118_instant",
    "retained_earnings_adjustments_to_retained_earnings_118_duration",
    "retained_earnings_appropriations_of_retained_earnings_118_duration",
    "retained_earnings_common_stock_118_duration",
    "retained_earnings_preferred_stock_118_duration",
    "retained_earnings_unappropriated_undistributed_subsidiary_earnings_118_duration",
    "revenues_from_storing_gas_of_others_account_489_4_306_duration",
    "revenues_from_transporation_of_gas_of_others_through_gathering_facilities_account_489_1_302_duration",
    "revenues_from_transportation_of_gas_of_others_through_transmission_facilities_account_489_2_304_duration",
    "revenues_from_transportation_of_gas_of_others_through_transmission_facilities_account_489_2_by_rate_schedule_304_duration",
    "revenues_from_transportation_of_gas_of_others_through_transmission_facilities_account_489_2_by_zone_304_duration",
    "securities_issued_or_assumed_and_securities_refunded_or_retired_during_the_year_255_1_duration",
    "security_holders_and_voting_powers_107_duration",
    "security_holders_and_voting_powers_107_instant",
    "security_holders_and_voting_powers_sequence_107_duration",
    "security_holders_and_voting_powers_sequence_107_instant",
    "shipper_supplied_gas_for_the_current_quarter_521_m1_duration",
    "shipper_supplied_gas_for_the_current_quarter_521_m2_duration",
    "shipper_supplied_gas_for_the_current_quarter_521_m3_duration",
    "shipper_supplied_gas_for_the_current_quarter_other_disposition_of_excess_gas_521_m1_duration",
    "shipper_supplied_gas_for_the_current_quarter_other_disposition_of_excess_gas_521_m2_duration",
    "shipper_supplied_gas_for_the_current_quarter_other_disposition_of_excess_gas_521_m3_duration",
    "shipper_supplied_gas_for_the_current_quarter_other_gas_acquired_to_meet_deficiency_521_m1_duration",
    "shipper_supplied_gas_for_the_current_quarter_other_gas_acquired_to_meet_deficiency_521_m2_duration",
    "shipper_supplied_gas_for_the_current_quarter_other_gas_acquired_to_meet_deficiency_521_m3_duration",
    "statement_of_accumulated_other_comprehensive_income_and_hedging_activities_117_duration",
    "statement_of_accumulated_other_comprehensive_income_and_hedging_activities_117_instant",
    "statement_of_cash_flows_120_duration",
    "statement_of_cash_flows_120_instant",
    "statement_of_cash_flows_cash_provided_by_outside_sources_120_duration",
    "statement_of_cash_flows_noncash_adjustments_to_cash_flows_from_operating_activities_120_duration",
    "statement_of_cash_flows_other_adjustments_from_financing_activities_120_duration",
    "statement_of_cash_flows_other_adjustments_from_investing_activities_120_duration",
    "statement_of_cash_flows_other_adjustments_from_operating_activities_120_duration",
    "statement_of_cash_flows_other_cash_outflows_for_plant_120_duration",
    "statement_of_cash_flows_other_payment_for_retirement_to_financing_acitivities_120_duration",
    "statement_of_income_114_duration",
    "summary_of_utility_plant_and_accumulated_provisions_for_depreciation_amortization_and_depletion_200_instant",
    "system_map_522_duration",
    "taxes_accrued_prepaid_and_charged_during_year_distribution_of_taxes_charged_show_utility_dept_where_applicable_and_acct_charged_262_duration",
    "taxes_accrued_prepaid_and_charged_during_year_distribution_of_taxes_charged_show_utility_dept_where_applicable_and_acct_charged_262_instant",
    "taxes_accrued_prepaid_and_charged_during_year_distribution_of_taxes_charged_total_262_duration",
    "taxes_accrued_prepaid_and_charged_during_year_distribution_of_taxes_charged_total_262_instant",
    "temporary_cash_investments_account_136_222_duration",
    "temporary_cash_investments_account_136_222_instant",
    "temporary_cash_investments_account_136_totals_222_duration",
    "temporary_cash_investments_account_136_totals_222_instant",
    "transactions_with_associated_affiliated_companies_provided_by_affiliated_company_358_duration",
    "transactions_with_associated_affiliated_companies_provided_by_affiliated_company_totals_358_duration",
    "transmission_and_compression_of_gas_by_others_account_858_332_duration",
    "transmission_and_compression_of_gas_by_others_account_858_totals_332_duration",
    "transmission_lines_514_duration",
    "transmission_lines_514_instant",
    "transmission_lines_total_514_duration",
    "transmission_lines_total_514_instant",
    "transmission_system_peak_deliveries_single_day_gas_transported_518_duration",
    "transmission_system_peak_deliveries_single_day_gas_withdrawn_518_duration",
    "transmission_system_peak_deliveries_single_day_other_operational_activities_518_duration",
    "transmission_system_peak_deliveries_single_day_peak_deliveries_518_duration",
    "transmission_system_peak_deliveries_three_day_gas_transported_518_duration",
    "transmission_system_peak_deliveries_three_day_gas_withdrawn_518_duration",
    "transmission_system_peak_deliveries_three_day_other_operational_activities_518_duration",
    "transmission_system_peak_deliveries_three_day_peak_deliveries_518_duration",
    "unamortized_debt_expense_account_181_258_duration",
    "unamortized_debt_expense_account_181_258_instant",
    "unamortized_debt_expense_premium_and_discount_on_long_term_debt_accounts_181_225_226_258_duration",
    "unamortized_debt_expense_premium_and_discount_on_long_term_debt_accounts_181_225_226_258_instant",
    "unamortized_gain_account_257_260_duration",
    "unamortized_gain_account_257_260_instant",
    "unamortized_loss_account_189_260_duration",
    "unamortized_loss_account_189_260_instant",
    "unamortized_loss_and_gain_on_reacquired_debt_account_189_257_260_duration",
    "unamortized_loss_and_gain_on_reacquired_debt_account_189_257_260_instant",
    "unrecovered_plant_and_regulatory_study_costs_account_182_2_230c_duration",
    "unrecovered_plant_and_regulatory_study_costs_account_182_2_230c_instant",
    "unrecovered_plant_and_regulatory_study_costs_account_182_2_totals_230c_duration",
    "unrecovered_plant_and_regulatory_study_costs_account_182_2_totals_230c_instant",
]


def extract_schedule_number(table_name: str) -> str:
    """Extract schedule number from XBRL table name.

    The schedule number is the last alphanumeric token before _duration or _instant.
    Examples:
      control_over_respondent_102_duration -> "102"
      identification_001_duration -> "1" (strip leading zeros)
      extraordinary_property_losses_account_182_1_230b_duration -> "230b"
      important_changes_during_the_quarter_year_108_1_duration -> "108-1"
      notes_to_financial_statements_122_1_duration -> "122.1"
      shipper_supplied_gas_for_the_current_quarter_521_m1_duration -> "521"
    """
    # Strip _duration or _instant suffix
    name = re.sub(r"_(duration|instant)$", "", table_name)

    # Strip _m1, _m2, _m3 suffix (monthly sub-tables)
    name = re.sub(r"_m[123]$", "", name)

    # Split into parts
    parts = name.split("_")

    # The last part should be the schedule number
    last = parts[-1]

    # Check if it's alphanumeric (e.g., 230a, 230b, 230c)
    if re.match(r"^\d+[a-z]?$", last):
        # Strip leading zeros from pure numeric, keep alphanumeric as-is
        if last.isdigit():
            return str(int(last))
        else:
            # e.g. "230a" -> "230a"
            # strip leading zeros from numeric part
            num_part = re.match(r"^(\d+)([a-z])$", last)
            if num_part:
                return str(int(num_part.group(1))) + num_part.group(2)
            return last

    # Could be something like "1" at end of a compound like "108_1" or "122_1"
    # Check second-to-last too
    if len(parts) >= 2:
        parts[-2]
        # Special cases:
        # important_changes_during_the_quarter_year_108_1 -> "108-1"
        # notes_to_financial_statements_122_1 -> "122.1"
        # investments_in_subsidiary_companies_account_123_1_224 -> last is "224"
        # securities_issued...255_1 -> "255.1" (but ends in _1 and is page 255.1)
        # Actually for these cases the LAST part IS the schedule, so let's re-check
        pass

    # Fall through - return last as-is (strip leading zeros)
    if last.isdigit():
        return str(int(last))
    return last


def get_schedule_number_from_table(table_name: str) -> str:
    """Get schedule number with special-case handling."""
    name = re.sub(r"_(duration|instant)$", "", table_name)
    name = re.sub(r"_m[123]$", "", name)
    parts = name.split("_")

    # Special compound schedule numbers:
    # important_changes_during_the_quarter_year_108_1 -> "108-1" (page 108)
    # notes_to_financial_statements_122_1 -> "122.1"
    # securities_issued_or_assumed_and_securities_refunded_or_retired_during_the_year_255_1
    #   -> "255.1" (page 255.1 in TOC)

    # Check for _N_1 pattern at end (compound schedule numbers)
    if len(parts) >= 2 and parts[-1] == "1" and parts[-2].isdigit():
        base = int(parts[-2])
        full_name_before = "_".join(parts[:-2])
        # "important_changes" -> 108-1 (actually the TOC says page 108)
        # But the XBRL table name is "important_changes_during_the_quarter_year_108_1"
        # TOC page reference is "108" with note "Important Changes During the Year"
        # However, there's also "108-1" as an XBRL schedule reference
        # The TOC shows page 108, so let's use "108"
        # But the task instructions say "108-1" for this table... let me use the task spec

        # notes_to_financial_statements_122_1 -> schedule "122.1" per task spec
        # securities_issued...255_1 -> schedule "255.1" per TOC (which shows "255.1")
        # important_changes_during_the_quarter_year_108_1 -> "108-1" per task spec

        if "notes_to_financial_statements" in full_name_before:
            return "122.1"
        elif "important_changes" in full_name_before:
            # TOC page reference is 108, not 108-1
            return "108"
        elif "securities_issued_or_assumed" in full_name_before:
            return "255.1"
        else:
            return str(base)

    last = parts[-1]

    if re.match(r"^\d+[a-z]$", last):
        # alphanumeric like 230a, 230b, 230c
        num_part = re.match(r"^(\d+)([a-z])$", last)
        if num_part:
            return str(int(num_part.group(1))) + num_part.group(2)

    if last.isdigit():
        num = int(last)
        # Special case: system_map_522 is actually schedule 522.1 per the TOC
        if num == 522 and "system_map" in name:
            return "522.1"
        return str(num)

    return last


def extract_description_from_div(div) -> str:
    """Extract useful description text from a schedule div."""
    if div is None:
        return ""

    full_text = div.get_text("\n", strip=True)
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    # Skip boilerplate header lines
    skip_patterns = [
        r"^Name of Respondent",
        r"^This report is",
        r"^\(\d+\)",
        r"^[☐✓]",
        r"^An Original",
        r"^A Resubmission",
        r"^Date of Report",
        r"^Year/Period of Report",
        r"^End of",
        r"^FERC FORM",
        r"^Page \d",
        r"^\d+$",  # lone numbers
        r"^Line N",
        r"^/",
    ]

    # Find the schedule title line (usually all caps or title case after headers)
    content_lines = []

    for line in lines:
        # Skip short lines
        if len(line) < 5:
            continue

        # Check if this is a boilerplate line
        is_skip = any(re.match(p, line, re.IGNORECASE) for p in skip_patterns)
        if is_skip:
            continue

        content_lines.append(line)

    if not content_lines:
        return ""

    # The first content line is usually the title, subsequent lines are instructions
    # We want the first 1-3 instruction/description lines after the title
    # Skip the title itself (first content line)
    if len(content_lines) > 1:
        desc_lines = content_lines[1:4]  # up to 3 lines of description
    else:
        desc_lines = content_lines[:1]

    # Join and clean up
    description = " ".join(desc_lines)
    # Clean up extra whitespace
    description = re.sub(r"\s+", " ", description).strip()
    # Truncate to reasonable length
    if len(description) > 500:
        # Find sentence boundary
        sentences = re.split(r"(?<=[.!?])\s+", description)
        desc = sentences[0]
        if len(sentences) > 1 and len(desc) < 200:
            desc = desc + " " + sentences[1]
        description = desc

    return description


def normalize_toc_page(page: str) -> str:
    """Normalize a TOC page reference to a schedule number."""
    page = page.strip()
    # Remove leading zeros from numeric parts
    # e.g. "001" -> "1", "110" -> "110", "122.1" -> "122.1", "230a" -> "230a"
    match = re.match(r"^(\d+)(\.\d+)?([a-z])?$", page)
    if match:
        num = int(match.group(1))
        decimal = match.group(2) or ""
        letter = match.group(3) or ""
        return str(num) + decimal + letter
    return page


# Map from schedule ID in HTML to friendly names for descriptions
DIV_ID_TO_SCHEDULE_NUM = {
    "ScheduleIdentificationAbstract": "1",
    "ScheduleListOfSchedulesAbstract": "2",
    "ScheduleGeneralInformationAbstract": "101",
    "ScheduleControlOverRespondentAbstract": "102",
    "ScheduleCorporationsControlledByRespondentAbstract": "103",
    "ScheduleSecurityHoldersAndVotingPowersAbstract": "107",
    "ScheduleImportantChangesDuringTheQuarterYearAbstract": "108",
    "ScheduleComparativeBalanceSheetAssetsAndOtherDebitsAbstract": "110",
    "ScheduleComparativeBalanceSheetLiabilitiesOtherCreditsAbstract": "110",  # same page range 110-112
    "ScheduleStatementOfIncomeAbstract": "114",
    "ScheduleStatementOfAccumulatedOtherComprehensiveIncomeAndHedgingActivitiesAbstract": "117",
    "ScheduleStatementOfRetainedEarningsAbstract": "118",
    "ScheduleStatementOfCashFlowsAbstract": "120",
    "ScheduleNotesToFinancialStatementsAbstract": "122.1",
    "ScheduleSummaryOfUtilityPlantAndAccumulatedProvisionsForDepreciationAmortizationAndDepletionAbstract": "200",
    "ScheduleGasPlantInServiceAbstract": "204",
    "ScheduleGasPropertyAndCapacityLeasedFromOthersAbstract": "212",
    "ScheduleGasPropertyAndCapacityLeasedToOthersAbstract": "213",
    "ScheduleGasPlantHeldForFutureUseAbstract": "214",
    "ScheduleConstructionWorkInProgressGasAbstract": "216",
    "ScheduleNonTraditionalRateTreatmentAffordedNewProjectsAbstract": "217",
    "ScheduleGeneralDescriptionOfConstructionOverheadProcedureAbstract": "218",
    "ScheduleAccumulatedProvisionForDepreciationOfGasUtilityPlantAbstract": "219",
    "ScheduleGasStoredAbstract": "220",
    "ScheduleInvestmentsAbstract": "222",
    "ScheduleInvestmentsInSubsidiaryCompaniesAbstract": "224",
    "SchedulePrepaymentsAbstract": "230a",
    "ScheduleExtraordinaryPropertyLossesAbstract": "230b",
    "ScheduleUnrecoveredPlantAndRegulatoryStudyCostsAbstract": "230c",
    "ScheduleOtherRegulatoryAssetsAbstract": "232",
    "ScheduleMiscellaneousDeferredDebitsAbstract": "233",
    "ScheduleAccumulatedDeferredIncomeTaxesAbstract": "234",
    "ScheduleCapitalStockAbstract": "250",
    "ScheduleCapitalStockSubscribedLiabilityForConversionPremiumOnAndInstallmentsReceivedOnAbstract": "252",
    "ScheduleOtherPaidInCapitalAbstract": "253",
    "ScheduleDiscountOnCapitalStockAbstract": "254",
    "ScheduleSecuritiesIssuedOrAssumedAndSecuritiesRefundedOrRetiredDuringTheYearAbstract": "255.1",
    "ScheduleLongTermDebtAbstract": "256",
    "ScheduleUnamortizedDebtExpensePremiumAndDiscountOnLongTermDebtAbstract": "258",
    "ScheduleUnamortizedLossAndGainOnReacquiredDebtAbstract": "260",
    "ScheduleReconciliationOfReportedNetIncomeWithTaxableIncomeForFederalIncomeTaxesAbstract": "261",
    "ScheduleTaxesAccruedPrepaidAndChargedDuringYearDistributionOfTaxesChargedAbstract": "262",
    "ScheduleMiscellaneousCurrentAndAccruedLiabilitiesAbstract": "268",
    "ScheduleOtherDeferredCreditsAbstract": "269",
    "ScheduleAccumulatedDeferredIncomeTaxesOtherPropertyAbstract": "274",
    "ScheduleAccumulatedDeferredIncomeTaxesOtherAbstract": "276",
    "ScheduleOtherRegulatoryLiabilitiesAbstract": "278",
    "ScheduleMonthlyQuantityRevenueDataByRateScheduleAbstract": "299",
    "ScheduleGasOperatingRevenuesAbstract": "300",
    "ScheduleRevenuesFromTransporationOfGasOfOthersThroughGatheringFacilitiesAbstract": "302",
    "ScheduleRevenuesFromTransportationOfGasOfOthersThroughTransmissionFacilitiesAbstract": "304",
    "ScheduleRevenuesFromStoringGasOfOthersAbstract": "306",
    "ScheduleOtherGasRevenuesAbstract": "308",
    "ScheduleDiscountedRateServicesAndNegotiatedRateServicesAbstract": "313",
    "ScheduleGasOperationAndMaintenanceExpensesAbstract": "317",
    "ScheduleExchangeAndImbalanceTransactionsAbstract": "328",
    "ScheduleGasUsedInUtilityOperationsAbstract": "331",
    "ScheduleTransmissionAndCompressionOfGasByOthersAbstract": "332",
    "ScheduleOtherGasSupplyExpensesAbstract": "334",
    "ScheduleMiscellaneousGeneralExpensesAbstract": "335",
    "ScheduleDepreciationDepletionAndAmortizationAbstract": "336",
    "ScheduleFactorsUsedInEstimatingDepreciationChargesAbstract": "338",
    "ScheduleParticularsConcerningCertainIncomeDeductionsAndInterestChargesAccountsAbstract": "340",
    "ScheduleRegulatoryCommissionExpensesAbstract": "350",
    "ScheduleEmployeePensionsAndBenefitsAbstract": "352",
    "ScheduleDistributionOfSalariesAndWagesAbstract": "354",
    "ScheduleChargesForOutsideProfessionalAndOtherConsultativeServicesAbstract": "357",
    "ScheduleTransactionsWithAssociatedAffiliatedCompaniesAbstract": "358",
    "ScheduleCompressorStationsAbstract": "508",
    "ScheduleGasStorageProjectsAbstract": "512",
    "ScheduleGasStorageProjectsByCapacitiesAbstract": "513",
    "ScheduleTransmissionLinesAbstract": "514",
    "ScheduleTransmissionSystemPeakDeliveriesAbstract": "518",
    "ScheduleAuxiliaryPeakingFacilitiesAbstract": "519",
    "ScheduleGasAccountNaturalGasAbstract": "520",
    "ScheduleShipperSuppliedGasForTheCurrentQuarterAbstract": "521",
    "ScheduleSystemMapsAbstract": "522.1",
}


# TOC data: schedule_num -> (title, div_id)
# Build from TOC table
def parse_toc(soup):
    """Parse the table of contents table."""
    tables = soup.find_all("table")
    toc_table = tables[7]

    schedules = {}
    rows = toc_table.find_all("tr")
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue
        page_cell = cells[2]
        title_cell = cells[1]

        page_text = page_cell.get_text(strip=True)
        title_text = title_cell.get_text(strip=True)

        if not page_text or not page_text[0].isdigit():
            continue

        # Get the link target from page cell
        link = page_cell.find("a")
        href = link.get("href", "") if link else ""
        div_id = href.lstrip("#") if href else ""

        # Get the page number
        page_num = normalize_toc_page(page_text)

        # Clean title: remove the abstract prefix (e.g., "ScheduleXxxAbstractTitle Text" -> "Title Text")
        # The format is "ScheduleXxxAbstractActual Title"
        clean_title = re.sub(r"^Schedule\w+Abstract", "", title_text)
        clean_title = re.sub(r"^[A-Z][a-zA-Z]+Abstract", "", clean_title)
        clean_title = clean_title.strip()

        if not clean_title:
            continue

        # Some entries might have same page number (e.g., both Discount on Capital Stock
        # and Capital Stock Expense are at page 254)
        # We'll keep the first occurrence for the main schedule, but track all
        key = (page_num, div_id or clean_title)
        schedules[key] = {
            "schedule": page_num,
            "title": clean_title,
            "div_id": div_id,
        }

    return schedules


def group_xbrl_by_schedule(xbrl_tables: list[str]) -> dict[str, list[str]]:
    """Group XBRL table names by schedule number."""
    by_schedule = {}
    for t in xbrl_tables:
        sched = get_schedule_number_from_table(t)
        if sched not in by_schedule:
            by_schedule[sched] = []
        by_schedule[sched].append(t)
    return by_schedule


def schedule_sort_key(schedule_num: str) -> tuple:
    """Sort key for schedule numbers."""
    # Handle forms like "1", "101", "230a", "230b", "122.1", "255.1", "108-1"
    match = re.match(r"^(\d+)([.-])?(\d+)?([a-z])?$", schedule_num)
    if match:
        major = int(match.group(1))
        match.group(2) or ""
        minor = int(match.group(3)) if match.group(3) else 0
        letter = match.group(4) or ""
        return (major, minor, letter)
    return (999999, 0, schedule_num)


# Custom descriptions for schedules where auto-extraction produces poor results
CUSTOM_DESCRIPTIONS = {
    "1": (
        "Identification",
        "Respondent's legal name, address, contact person, and whether the filing is an original or resubmission.",
    ),
    "2": (
        "List of Schedules (Natural Gas Company)",
        "Index of all Form 2 schedules; filer marks each as complete or not applicable.",
    ),
}


def main():
    with open(HTML_PATH, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Parse TOC
    toc_schedules = parse_toc(soup)
    print(f"Found {len(toc_schedules)} TOC entries")

    # Build schedule_num -> {title, div_id} mapping
    # There may be duplicate page numbers (e.g. 254 has two schedules)
    sched_info = {}  # schedule_num -> list of {title, div_id}
    for key, info in toc_schedules.items():
        snum = info["schedule"]
        if snum not in sched_info:
            sched_info[snum] = []
        sched_info[snum].append(info)

    # Group XBRL tables by schedule
    xbrl_by_sched = group_xbrl_by_schedule(XBRL_TABLES)
    print(
        f"Schedule numbers from XBRL tables: {sorted(xbrl_by_sched.keys(), key=schedule_sort_key)}"
    )

    # Verify all XBRL tables are covered
    all_xbrl_assigned = set()

    # Build final schedule entries
    # We need to decide how to handle page 254 which has two schedules
    # (Discount on Capital Stock and Capital Stock Expense)
    # Both have XBRL tables at page 254, so we'll merge them into one entry

    # Similarly, pages 110/112 for Comparative Balance Sheet
    # Both have XBRL tables at page 110, so one entry

    # Build mapping: schedule_num -> entry
    entries = {}

    # First pass: use TOC to build entries
    for snum, infos in sched_info.items():
        # Check for custom title/description override
        if snum in CUSTOM_DESCRIPTIONS:
            title, description = CUSTOM_DESCRIPTIONS[snum]
        else:
            # Use first entry's div_id for description
            primary_info = infos[0]
            div_id = primary_info["div_id"]

            if div_id:
                div = soup.find("div", id=div_id)
                description = extract_description_from_div(div)
            else:
                description = ""

            # For title, use first entry's title
            title = primary_info["title"]

        xbrl_tables = sorted(xbrl_by_sched.get(snum, []))
        all_xbrl_assigned.update(xbrl_tables)

        entries[snum] = {
            "title": title,
            "description": description,
            "pudl_tables": [],
            "xbrl_tables": xbrl_tables,
            "dbf_tables": [],
            "schedule": snum,
            "ferc_accounts": [],
        }

    # Check for XBRL tables not assigned to a TOC schedule
    unassigned = set(XBRL_TABLES) - all_xbrl_assigned
    if unassigned:
        print("\nUnassigned XBRL tables:")
        for t in sorted(unassigned):
            snum = get_schedule_number_from_table(t)
            print(f"  {t} -> schedule {snum}")

    # Sort by schedule number
    sorted_entries = sorted(
        entries.values(), key=lambda e: schedule_sort_key(e["schedule"])
    )

    # Write output
    with open(OUTPUT_PATH, "w") as f:
        json.dump(sorted_entries, f, indent=2)
        f.write("\n")

    print(f"\nWrote {len(sorted_entries)} schedule entries to {OUTPUT_PATH}")

    # Show entries with no description
    no_desc = [e for e in sorted_entries if not e["description"]]
    if no_desc:
        print(f"\nEntries with no description ({len(no_desc)}):")
        for e in no_desc:
            print(f"  Schedule {e['schedule']}: {e['title']}")

    # Show entries with no XBRL tables
    no_xbrl = [e for e in sorted_entries if not e["xbrl_tables"]]
    if no_xbrl:
        print(f"\nEntries with no XBRL tables ({len(no_xbrl)}):")
        for e in no_xbrl:
            print(f"  Schedule {e['schedule']}: {e['title']}")


if __name__ == "__main__":
    main()
