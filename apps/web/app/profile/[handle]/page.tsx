export default function ProfilePage({ params }: { params: { handle: string } }): JSX.Element {
  return (
    <section className="card">
      <h1>Profile · {params.handle}</h1>
      <p className="muted">Alpha placeholder: activity and submission history will be expanded in later milestones.</p>
    </section>
  );
}
