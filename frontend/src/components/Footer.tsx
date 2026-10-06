import { Link } from 'react-router-dom'
import YaleMark from './YaleMark'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-pennants" aria-hidden="true" />
      <p className="footer-chant">Bulldogs! Bulldogs! Bow wow wow!</p>
      <div className="footer-inner">
        <div className="footer-col">
          <div className="footer-brand">
            <YaleMark size={36} />
            Campus Customs
          </div>
          <p>Yale Bulldog Blue · officially licensed Yale apparel</p>
          <p>57 Broadway, New Haven, CT 06511</p>
        </div>
        <div className="footer-col">
          <p className="footer-head">Shop</p>
          <div className="footer-links">
            <Link to="/products?category=hoodies">Hoodies</Link>
            <Link to="/products?category=crewnecks">Crewnecks</Link>
            <Link to="/products?category=tees">T-Shirts</Link>
            <Link to="/products?q=Harvard">The Game</Link>
          </div>
        </div>
        <div className="footer-col">
          <p className="footer-head">Help</p>
          <div className="footer-links">
            <Link to="/about">Shipping & returns</Link>
            <Link to="/signup">Create an account</Link>
            <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>
            <span>(475) 301-4205</span>
          </div>
        </div>
      </div>
      <p className="footer-fine">
        A class project inspired by Yale Bulldog Blue by Campus Customs. Boola boola. 💙
      </p>
    </footer>
  )
}
