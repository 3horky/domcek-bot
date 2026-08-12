import { Link } from 'react-router-dom'

import { Button } from '../components/ui/button'

export function NotFoundPage() {
  return (
    <section className="empty-state not-found-state">
      <p className="eyebrow">Stránka sa nenašla</p>
      <h1>Táto stránka neexistuje</h1>
      <p>Skontrolujte adresu alebo sa vráťte na prehľad najbližších oznamov.</p>
      <Button nativeButton={false} render={<Link to="/" />}>
        Späť na prehľad
      </Button>
    </section>
  )
}
