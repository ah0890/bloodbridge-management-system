import { Construction } from "lucide-react";
import { PageHeader } from "@/components/ui/card";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";

/** Explicitly marks a section that is not implemented yet, so no visible action silently does nothing. */
export function UnavailablePage({ title, milestone }: { title: string; milestone: string }) {
  return (
    <>
      <PageHeader title={title} />
      <Card>
        <EmptyState
          icon={<Construction className="size-8" />}
          title="Not available yet"
          description={`This section is scheduled for ${milestone}. It is listed so that navigation and permissions can be verified.`}
        />
      </Card>
    </>
  );
}

export function NotFoundPage() {
  return <EmptyState title="Page not found" description="The page you requested does not exist." className="min-h-[50vh]" />;
}
