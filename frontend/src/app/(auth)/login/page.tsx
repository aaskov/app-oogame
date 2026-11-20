import { LoginForm } from "@/components/auth/LoginForm";
import { Card } from "@/components/ui/Card";

export default function LoginPage() {
  return (
    <main className="flex flex-1 items-start justify-center p-4 sm:items-center">
      <Card className="w-full max-w-sm">
        <LoginForm />
      </Card>
    </main>
  );
}
