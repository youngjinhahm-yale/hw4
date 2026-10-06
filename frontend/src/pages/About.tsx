import { Link } from 'react-router-dom'

export default function About() {
  return (
    <section className="section about">
      <h1 className="page-title">About Campus Customs</h1>
      <p className="lead">
        We're the folks behind Yale Bulldog Blue, a small New Haven shop that turns school
        spirit into clothes you'll reach for every morning.
      </p>

      <div className="about-grid">
        <div>
          <h2>What we do</h2>
          <p>
            Campus Customs carries officially licensed Yale merchandise. That covers sweatshirts and
            tees, plus jackets, residential college gear, and pieces for proud parents and
            grandparents. Every design uses real university marks, so what you buy is the genuine
            article.
          </p>
          <p>
            Much of our line is printed to order, which keeps us from overstocking and lets us
            carry niche favorites like your college's quarter-zip or a Harvard–Yale game-day tee.
          </p>
        </div>
        <div>
          <h2>Find us</h2>
          <p>
            Our shop sits at <strong>57 Broadway, New Haven, CT 06511</strong>, a short walk from
            Old Campus. Online, we ship across the U.S. and to dozens of countries.
          </p>
          <h2>Orders & returns</h2>
          <ul>
            <li>Most orders are produced within 5–8 business days and usually ship by UPS.</li>
            <li>You'll get a tracking email as soon as your package leaves.</li>
            <li>
              Return unworn items with tags within 30 days of shipping. Custom and alumni items are
              final sale.
            </li>
            <li>
              Need help? Email orderdept@campuscustoms.com or call (475) 301-4205.
            </li>
          </ul>
        </div>
      </div>

      <div className="about-cta">
        <p>Not sure what fits? Our chat helper can check sizes and stock for you.</p>
        <Link to="/products" className="btn">
          Browse the shop
        </Link>
      </div>
    </section>
  )
}
