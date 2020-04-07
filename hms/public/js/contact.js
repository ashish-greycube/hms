frappe.ui.form.on("Contact", {
  refresh: function (frm) {
    frm.page.add_inner_button("Capture ID", function (params) {
      capture_camera(frm);
      // not using frappe.ui.Capture as it does not close camera after submit, and image proportions get distorted
      // let capture = new frappe.ui.Capture({ animate: false, error: true });
    });
  },
});

function capture_camera(frm) {
  //TODO: refactor into generic class

  let dialog = new frappe.ui.Dialog({
    title: __("Attach Contact ID"),
    fields: [
      {
        fieldname: "snap_btn",
        fieldtype: "Button",
        label: "Snap",
        click: function () {
          $wrapper = dialog.fields_dict.video_area.$wrapper;
          dialog.canvas = $wrapper.find("#canvas").get(0);
          var context = dialog.canvas.getContext("2d");
          context.drawImage(dialog.video, 0, 0, 320, 240);
        },
        // input_class: "btn-warning",
        input_css: {
          "margin-top": "20px;",
        },
      },
      {
        // "label" : "Name",
        fieldname: "video_area",
        fieldtype: "HTML",
        options: `
        <div class="content text-center">
          <video id="video" width="320" height="240" autoplay></video>
          <canvas id="canvas" width="320" height="240"></canvas>
        </div>
        `,
      },
    ],
    primary_action_label: __("Attach"),
    primary_action: function () {
      for (let t of dialog.video.srcObject.getVideoTracks()) {
        t.stop();
      }
      dialog.hide();
      var image = dialog.canvas.toDataURL("image/jpeg", 0.1);
      frappe.call({
        method: "hms.hms.controllers.reservation.attach_contact_id",
        args: {
          docname: frm.doc.name,
          date: moment().format("D-MMM-YYYY"),
          data_url: image,
        },
        callback: function (r) {
          frm.reload_doc();
        },
      });
    },
  });
  var $wrapper;
  $wrapper = dialog.fields_dict.video_area.$wrapper;
  dialog.video = $wrapper.find("#video").get(0);
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    // Not adding `{ audio: true }` since we only want video now
    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then(function (stream) {
        //video.src = window.URL.createObjectURL(stream);
        dialog.video.srcObject = stream;
        dialog.video.play();
      });
  }
  dialog.show();
  //
}
