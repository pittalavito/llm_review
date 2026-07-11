/** Temporary stand-in for sections not yet migrated. */
export default function Placeholder({ title }: { title: string }) {
  return (
    <div className="section">
      <h2 className="section__title">{title}</h2>
      <p className="section__desc">Sezione in migrazione — usa la UI classica su / per ora.</p>
    </div>
  );
}
