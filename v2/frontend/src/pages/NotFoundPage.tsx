import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="empty-state">
      <p className="eyebrow">404</p>
      <h1>Táto stránka neexistuje</h1>
      <p>Skontroluj adresu alebo sa vráť na prehľad najbližšieho balíka.</p>
      <Link to="/">Späť na prehľad</Link>
    </section>
  )
}
