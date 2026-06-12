import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="app-shell">
      <div className="hero-bleed">
        <section className="surface main-pad landing-minimal">
          <div className="landing-brand">SchemeSathi</div>

          <h1 className="hero-title landing-title">Find government welfare schemes you are eligible for.</h1>

          <p className="subtitle landing-copy">
            A simple, secure chatbot for Indian users to check eligibility, upload supporting documents, and get
            source-backed guidance.
          </p>

          <div className="cta-row landing-cta">
            <Link href="/auth" className="primary-button primary-link" aria-label="Continue with Google">
              Continue with Google
            </Link>
          </div>

          <section className="trust-section" aria-label="Privacy and trust">
            <p className="trust-title">Privacy first</p>
            <p className="helper-text">
              We only collect the details needed to assess eligibility. Uploaded documents and profile information are
              used to improve scheme matching.
            </p>
          </section>
        </section>
      </div>
    </main>
  );
}
