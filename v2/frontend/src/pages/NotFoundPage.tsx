import { Link } from 'react-router-dom'

import { Button } from '../components/ui/button'

export function NotFoundPage() {
  return (
    <section className="empty-state not-found-state">
      <p className="eyebrow">404</p>
      <h1>Táto stránka neexistuje</h1>
      <p>Skontroluj adresu alebo sa vráť na prehľad najbližšieho balíka.</p>
      <Button render={<Link to="/" />}>Späť na prehľad</Button>
    </section>
  )
}
