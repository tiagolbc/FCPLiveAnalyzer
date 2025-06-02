FCP Live Analyzer

FCP Live Analyzer is a software tool designed specifically for singers, vocal coaches, researchers, and voice scientists. This tool enables comprehensive real-time and offline acoustic analysis, focusing on the Formant Cluster Prominence (FCP), an important metric for evaluating vocal projection and resonance, especially related to the singer's formant.

What is Formant Cluster Prominence (FCP)?

Formant Cluster Prominence (FCP) quantifies how pronounced the cluster of higher formants (typically between 2–4 kHz) is relative to the general spectral trend of the voice. This prominence directly correlates with the clarity, brilliance, and projection capacity characteristic of well-trained singing voices, especially in classical music.

Key Features

Real-time Analysis (LIVE Mode): Provides immediate feedback on vocal performance, assisting singers and vocal coaches during practice sessions.

Load Audio Analysis: Allows offline analysis of pre-recorded audio files, suitable for detailed research and documentation.

Long-Term Average Spectrum (LTAS): Accurately calculates and displays LTAS, facilitating detailed acoustic research.

Detailed Calculations: Performs precise calculations including Lmax for different frequency bands, linear spectral trend, and FCP values.

Dynamic Visualization: Clearly displays the LTAS and highlights the crucial 2-4 kHz frequency band in real-time.

Export Results: Enables exporting analyzed data as CSV for further statistical analysis or documentation.

Splash Screen: Smooth startup with a professional, visually appealing splash screen.

Usage

Running the Software

Download the latest release from the releases page.

Unzip and execute the application (FCP_Live_Analyzer.exe).

Real-Time Analysis (LIVE Mode)

Connect a microphone.

Click LIVE to begin real-time analysis.

Monitor your vocal output and observe changes in real-time FCP.

The mean FCP value updates continuously, providing cumulative feedback.

Analyzing Pre-recorded Files

Click LOAD to select a WAV audio file.

After loading, view detailed LTAS plots and FCP values.

Play the audio and observe dynamic feedback on vocal performance.

Export the data using the EXPORT CSV button.

Technical Details

FCP calculation is performed using the following formula:



Lmax(2-4 kHz): Maximum LTAS amplitude between 2 and 4 kHz.

Trend(f_peak): Linear trend amplitude at the frequency of the maximum within the 2-4 kHz range.

Requirements

The software is developed in Python and requires the following packages:

numpy

matplotlib

sounddevice

scipy

parselmouth

pillow

To install dependencies:

pip install -r requirements.txt

Contributing

Contributions are welcome! Please follow the standard GitHub workflow:

Fork the repository.

Create your feature branch (git checkout -b feature/YourFeature).

Commit your changes (git commit -m 'Add YourFeature').

Push to the branch (git push origin feature/YourFeature).

Open a Pull Request.

Citation

If you use this software in your research, please cite it as:

Cruz, T. L. B. (2024). FCP Live Analyzer: Real-Time Acoustic Analysis for Singers [Software]. Retrieved from https://github.com/yourusername/FCPLiveAnalyzer

License

This software is licensed under the MIT License. See LICENSE.txt for details.

Contact

Tiago Lima Bicalho Cruz, PhD

Email: tiagolbc@gmail.com

Enjoy your vocal explorations and analysis with FCP Live Analyzer!
