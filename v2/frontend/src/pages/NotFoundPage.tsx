import { Link } from 'react-router-dom'

import { buttonVariants } from '../components/ui/button'

export function NotFoundPage() {
  return (
    <section className="empty-state not-found-state">
      <p className="eyebrow">Stránka sa nenašla</p>
      <h1>Táto stránka neexistuje</h1>
      <p>Skontrolujte adresu alebo sa vráťte na prehľad najbližších oznamov.</p>
      <Link className={buttonVariants()} to="/">
        Späť na prehľad
      </Link>
    </section>
  )
}
