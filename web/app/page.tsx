import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const RANKING_PLACEHOLDERS = [
  { title: "50m Libre", note: "Ranking nacional" },
  { title: "100m Espalda", note: "Ranking nacional" },
  { title: "200m Pecho", note: "Ranking por liga" },
];

export default function HomePage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-10 px-4 py-10 sm:py-16">
      <section className="flex flex-col items-start gap-4 text-left">
        <span className="text-4xl" aria-hidden="true">
          🏊
        </span>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          FECNA Natación
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          Rankings, fichas de nadadores y programas de campeonato de la
          federación, en un solo lugar. Busca un nadador, revisa sus mejores
          tiempos o sigue el cronograma de un campeonato.
        </p>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-medium">
          Ranking{" "}
          <span className="font-normal text-muted-foreground">
            (próximamente en B3)
          </span>
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {RANKING_PLACEHOLDERS.map((item) => (
            <Card key={item.title}>
              <CardHeader>
                <CardTitle>{item.title}</CardTitle>
                <CardDescription>{item.note}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
