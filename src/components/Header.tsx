import React from 'react';
import './Header.css'; // Assuming you will create a Header.css for specific styles

const Header: React.FC = () => {
    return (
        <header className="header">
            <div className="logo">
                <img src="/assets/logo.svg" alt="INFORMS Butler Chapter Logo" />
            </div>
            <nav className="navigation">
                <ul>
                    <li><a href="#home">Home</a></li>
                    <li><a href="#about">About</a></li>
                    <li><a href="#events">Events</a></li>
                    <li><a href="#contact">Contact</a></li>
                </ul>
            </nav>
        </header>
    );
};

export default Header;