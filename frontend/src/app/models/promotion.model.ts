export interface Promotion {
  Promo_Year: number | null;
  Region: string;
  Country: string;
  Category: string;
  Macro_Category: string;
  Brand: string;
  Week: string; // dd-mm-yyyy format
  Sales_Units: number;
  Price: number;
  Promotion: string;
  Start_Seas: string; // dd-mm-yyyy format
  End_Seas: string; // dd-mm-yyyy format
  Seasonality: number;
  Predicted_Sales: number;
  Baseline_Sales: number;
  Incremental_Sales: number;
  PromoID: string;
  Promo_Days: number;
  Half_Year: string;
  Promotion_Status: string;
  Event_Count: number;
  Planned_Event_Count: number;
  Start_Prom: string; // dd-mm-yyyy format
  End_Prom: string; // dd-mm-yyyy format
  Actual_Promo_Sales_Volume_Uplift: number;
  Planned_Promo_Sales_Volume_Uplift: number;
  Sales_Value: number;
  Baseline_Sales_Value: number;
  Actual_Promo_Sales_Value: number;
  Planned_Promo_Sales_Value: number;
  'Actual_Promo_Sales_Value_Uplift_PromoID_%': number;
  'Planned_Promo_Sales_Value_Uplift_PromoID_%': number;
  'Actual_Promo_Sales_Value_Uplift_%': number;
  'Planned_Promo_Sales_Value_Uplift_%': number;
  Actual_Sales_Value: number;
  Actual_Event_Spent: number;
  Planned_Event_Spent: number;
  COGS: number;
  Gross_Profit: number;
  Planned_Gross_Profit: number;
  'ROI%_PromoID': number;
  Baseline_Value: number;
  Planned_iGP: number;
  'Planned_ROI%_PromoID': number;
  'ROI%': number;
  'Planned_ROI%': number;
  'Actual_Gross_Margin_PromoID_%': number;
  'Planned_Gross_Margin_PromoID_%': number;
  'Actual_Gross_Margin_%': number;
  'Planned_Gross_Margin_%': number;
  Listing_Price: number;
  Incremental_Sales_Adjusted: number;
  Incremental_TO: number;
  Actual_Total_TO: number;
  Planned_Total_TO: number;
  Actual_Gross_Sales_Value: number;
  Planned_Gross_Sales_Value: number;
  'Actual Net Promo Incr Volume (Units)': number;
  Actual_RAG: string;
  Planned_RAG: string;
  Planned_Red: number;
  Planned_Amber: number;
  Planned_Green: number;
  Actual_Red: number;
  Actual_Amber: number;
  Actual_Green: number;
  Channel_Customer: string;
  ProductDescription: string;
  Packsize: string;
  Quarter?: string;
}
