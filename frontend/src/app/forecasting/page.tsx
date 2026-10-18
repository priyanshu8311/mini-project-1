import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Play } from "lucide-react";

export default function ForecastingPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Demand Forecasting
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Machine learning time-series models (XGBoost / Prophet) predicting SKU velocity.
          </p>
        </div>
        <Button variant="primary" size="sm">
          <Play className="w-4 h-4 mr-1.5" />
          Trigger Forecast Run
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Forecast Pipeline</CardTitle>
            <Badge variant="neutral">Offline Batch Ready</Badge>
          </div>
          <CardDescription>
            Pulls from sales_history and outputs daily/weekly predictions with confidence intervals.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-12 text-center text-sm text-[#64748b] border border-dashed border-[#cbd5e1] rounded-lg">
            <p className="font-medium text-[#0f172a]">No forecast jobs generated yet</p>
            <p className="text-xs text-[#94a3b8] mt-1">Requires at least 30 days of sales history to calculate predictive trends.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
