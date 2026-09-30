document.addEventListener('DOMContentLoaded', () => {
  const map = document.querySelector('#polar-map');
  if (map && window.L) {
    const polarMap = L.map(map, { zoomControl: true }).setView([-35, 30], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors' }).addTo(polarMap);
    const stations = [
      [-70.7693, 11.7339, 'Maitri Research Station', 'Atmospheric science and glaciology'],
      [-69.4076, 76.1874, 'Bharati Research Station', 'Oceanography and climate science'],
      [78.9232, 11.9230, 'Ny-Alesund field site', 'Arctic climate observations'],
      [20.5937, 78.9629, 'India', 'Research coordination']
    ];
    stations.forEach(([lat, lng, name, focus]) => L.marker([lat, lng]).addTo(polarMap).bindPopup(`<b>${name}</b><br>${focus}`));
  }
  const detailMap = document.querySelector('#detail-map');
  if (detailMap && window.L) {
    const lat = Number(detailMap.dataset.lat), lng = Number(detailMap.dataset.lng);
    const expeditionMap = L.map(detailMap, { zoomControl: false }).setView([lat, lng], 4);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(expeditionMap);
    L.marker([lat, lng]).addTo(expeditionMap).bindPopup('Expedition location').openPopup();
  }
});