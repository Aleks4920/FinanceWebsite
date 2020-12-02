function startCounting() {
    const counters = document.querySelectorAll('.counter');

    counters.forEach((counter) => {
        anime({
            targets: counter,
            innerHTML: [0, counter.getAttribute('data-count')],
            easing: 'easeInOutSine',
            round: 1,
            duration: 2000,
        })
    });
}

document.body.addEventListener('click', () => {
    startCounting();
});

startCounting();