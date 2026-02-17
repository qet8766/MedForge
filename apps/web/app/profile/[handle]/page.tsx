import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export default async function ProfilePage({
  params,
}: {
  params: { handle: string } | Promise<{ handle: string }>;
}): Promise<React.JSX.Element> {
  const resolvedParams = await params;
  const initials = resolvedParams.handle.slice(0, 2).toUpperCase();

  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <Avatar className="size-14">
              <AvatarFallback className="bg-primary/20 text-primary text-lg">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div>
              <CardTitle className="text-2xl">{resolvedParams.handle}</CardTitle>
              <CardDescription>Member profile</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Alpha placeholder: activity and submission history will be expanded in later milestones.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
