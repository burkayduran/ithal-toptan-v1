import { cn } from "@/lib/utils";

interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  narrow?: boolean;
}

export default function PageContainer({ children, className, narrow }: PageContainerProps) {
  return (
    <main
      className={cn(
        "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10",
        narrow && "max-w-4xl",
        className
      )}
    >
      {children}
    </main>
  );
}
