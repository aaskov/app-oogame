import { RegisterForm } from "@/components/auth/RegisterForm";
import { Card } from "@/components/ui/Card";

export default function RegisterPage() {
  return (
    <main className="flex flex-1 items-start justify-center p-4 sm:items-center">
      <Card className="w-full max-w-sm">
        <RegisterForm />
      </Card>
    </main>
  );
}
