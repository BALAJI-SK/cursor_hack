package com.chakra.comicreader.ui.about

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.chakra.comicreader.ui.brand.ChikaWordmark
import com.chakra.comicreader.ui.brand.OchreBadge
import com.chakra.comicreader.ui.brand.comicShadow
import com.chakra.comicreader.ui.brand.halftone
import com.chakra.comicreader.ui.theme.Anton
import com.chakra.comicreader.ui.theme.Archivo
import com.chakra.comicreader.ui.theme.Cream
import com.chakra.comicreader.ui.theme.CreamMuted
import com.chakra.comicreader.ui.theme.Crimson
import com.chakra.comicreader.ui.theme.Ink
import com.chakra.comicreader.ui.theme.Ochre

private const val DONATION_URL = "https://batunii.github.io"

@Composable
fun AboutScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val version = remember {
        runCatching {
            context.packageManager.getPackageInfo(context.packageName, 0).versionName
        }.getOrNull() ?: "—"
    }

    Box(Modifier.fillMaxSize().background(Ink)) {
        Box(Modifier.matchParentSize().halftone(Crimson, alpha = 0.05f))

        // Back button.
        Box(
            Modifier
                .statusBarsPadding()
                .padding(start = 12.dp, top = 8.dp)
                .size(38.dp)
                .clip(CircleShape)
                .background(Cream.copy(alpha = 0.12f))
                .clickable(onClick = onBack),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.AutoMirrored.Filled.ArrowBack, "Back",
                tint = Cream, modifier = Modifier.size(18.dp),
            )
        }

        Column(
            Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .padding(horizontal = 28.dp)
                .padding(top = 72.dp, bottom = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            ChikaWordmark()
            Spacer(Modifier.size(12.dp))
            OchreBadge("VERSION $version")
            Spacer(Modifier.size(14.dp))
            Text(
                "Made with ❤️ by Chakra",
                fontFamily = Archivo,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp,
                color = Cream,
            )

            Spacer(Modifier.size(36.dp))

            Text(
                "Chika is a comic reader that detects panels on-device and guides you through each " +
                    "page, panel by panel.",
                fontFamily = Archivo,
                fontWeight = FontWeight.Medium,
                fontSize = 13.sp,
                lineHeight = 19.sp,
                color = Cream,
            )

            Spacer(Modifier.weight(1f))

            // Donation call-to-action.
            Text(
                "Chika is free and made with care. If it brings you joy, you can support its making.",
                fontFamily = Archivo,
                fontWeight = FontWeight.Medium,
                fontSize = 12.sp,
                lineHeight = 17.sp,
                color = CreamMuted,
            )
            Spacer(Modifier.size(14.dp))
            Row(
                Modifier
                    .fillMaxWidth()
                    .comicShadow(offset = 4.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(Crimson)
                    .clickable {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(DONATION_URL)))
                    }
                    .padding(vertical = 14.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Default.Favorite, contentDescription = null, tint = Cream, modifier = Modifier.size(18.dp))
                Spacer(Modifier.size(10.dp))
                Text(
                    "SUPPORT / DONATE",
                    fontFamily = Anton,
                    fontSize = 15.sp,
                    letterSpacing = 0.5.sp,
                    color = Cream,
                )
            }
            Spacer(Modifier.size(6.dp))
            Text(
                "batunii.github.io",
                fontFamily = Archivo,
                fontWeight = FontWeight.SemiBold,
                fontSize = 11.sp,
                color = Ochre,
                modifier = Modifier
                    .clickable {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(DONATION_URL)))
                    }
                    .padding(top = 2.dp),
            )
        }
    }
}
