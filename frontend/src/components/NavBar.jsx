import { NavLink } from 'react-router-dom'
import './NavBar.css'

function linkClassName({ isActive }) {
  return isActive ? 'nav-link active' : 'nav-link'
}

function NavBar() {
  return (
    <nav className="nav-bar">
      <NavLink to="/" end className={linkClassName}>
        Dashboard
      </NavLink>
      <NavLink to="/browse" className={linkClassName}>
        Browse
      </NavLink>
      <NavLink to="/admin" className={linkClassName}>
        Admin
      </NavLink>
    </nav>
  )
}

export default NavBar
