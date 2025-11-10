function scrollToSection(id) {
  document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
}

// Splash screen hide after 5 seconds
setTimeout(() => {
  document.getElementById("splash").style.display = "none";
}, 5000);