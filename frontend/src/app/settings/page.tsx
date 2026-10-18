import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
          Settings & Integrations
        </h1>
        <p className="text-sm text-[#64748b] mt-1">
          Multi-channel synchronization and platform configurations.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Shopify Integration</CardTitle>
              <Badge variant="neutral">Not Connected</Badge>
            </div>
            <CardDescription>
              Two-way inventory and order synchronization with Shopify stores.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" size="sm">Configure Shopify</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Square POS Integration</CardTitle>
              <Badge variant="neutral">Not Connected</Badge>
            </div>
            <CardDescription>
              Real-time POS sale stock decrement and catalog sync.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" size="sm">Configure Square</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
