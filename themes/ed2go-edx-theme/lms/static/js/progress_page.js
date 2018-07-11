$(document).ready(function() {
  var $progressBars = $('.progress-bar'),
      progressBarOptions = {
          bars: {
              align: 'center',
              barWidth: 2,
              horizontal: true,
              lineWidth: 0.4
          },
          grid: {
              borderWidth: 0,
              margin: 0,
              minBorderMargin: 0
          },
          series: {
              bars: {
                  show: true
              }
          },
          xaxis: {
              max: 100,
              show: false
          },
          yaxis: {
              max: 1,
              show: false
          }
      };

  $progressBars.each(function() {
      var progress = $(this).data('progress');
      var dataSet = [{
          data: [[0, 0], [progress, 0]],
          color: "#00b4ff",
          label: progress + '%'
      }];

      $.plot($(this), dataSet, progressBarOptions);
      $('canvas.base', this).css('border-radius', '8px');
  });
});
