import Link from "next/link";
export default function NotFound() {
  return (
    <section className="empty-state">
      <h1>That road doesn’t lead here.</h1>
      <p>
        The page may have moved. The traffic overview is a good place to start.
      </p>
      <Link href="/" className="button primary">
        Back to overview
      </Link>
    </section>
  );
}
